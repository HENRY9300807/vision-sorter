from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import Qt, QPointF, QEvent
import cv2
import os
import sip  # PyQt5에서 객체 삭제 여부 확인용

from package.image_utils import to_pixmap, draw_points, highlight_rgb, make_pixel_map
from package.color_utils import add_color_def, save_defs, clear_defs
from package.operation import (
    DRAW_POINT_RADIUS, DRAW_POINT_LIMIT, UI_UPDATE_INTERVAL,
    SPHERE_RADIUS, PICTURE_DIR
)

UI_FILE = Path(__file__).resolve().with_name("mainwindow.ui")


class SafeViewPainter(QtCore.QObject):
    """
    QGraphicsView.viewport()에 이벤트 필터를 달아 좌클릭 드래그로 점(브러시)을 찍는다.
    - scene()/pixmap 유무 점검 → 없으면 조용히 무시(튕김 방지)
    - 확대/축소/스크롤과 호환(mapToScene 사용)
    """
    def __init__(self, root: QtWidgets.QWidget, view: QGraphicsView,
                 color_selector, radius: int = 8, auto_clear_on_next: bool = True):
        super().__init__(root)
        self.view = view
        self.color_selector = color_selector
        self.radius = max(1, int(radius))
        self._items = []

        # 씬 보장
        if self.view.scene() is None:
            self.view.setScene(QGraphicsScene(self.view))

        # 품질/기준점 설정
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.view.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # viewport에 필터 장착(중요)
        self.view.viewport().installEventFilter(self)

        # 다음 이미지로 넘어갈 때 자동 초기화(옵션)
        if auto_clear_on_next:
            nb = root.findChild(QtWidgets.QPushButton, "nextButton")
            if nb:
                nb.clicked.connect(self.clear)

    def clear(self):
        sc = self.view.scene()
        if not sc:
            self._items.clear()
            return
        # 목록을 먼저 복사해두고, 내부 리스트는 즉시 비움(중복 remove 방지)
        items = list(self._items)
        self._items.clear()
        for it in items:
            try:
                if it is None or sip.isdeleted(it):
                    continue
                # 아이템이 아직 어떤 scene에 붙어 있으면 그 scene에서 제거
                owner = it.scene()
                if owner is not None:
                    owner.removeItem(it)
            except Exception:
                pass

    def _has_any_pixmap(self) -> bool:
        sc = self.view.scene()
        if not sc:
            return False
        # 장면의 첫 번째 PixmapItem 유무만 확인 (없으면 그리지 않음)
        for it in sc.items():
            if isinstance(it, QGraphicsPixmapItem):
                return True
        return False

    def _draw_dot(self, pos):
        if not self._has_any_pixmap():
            return
        scene_pt = self.view.mapToScene(pos)
        r = self.radius
        color = self.color_selector()
        pen = QtGui.QPen(color)
        pen.setWidth(0)
        brush = QtGui.QBrush(color)
        item = self.view.scene().addEllipse(scene_pt.x()-r, scene_pt.y()-r, 2*r, 2*r, pen, brush)
        item.setZValue(10)
        self._items.append(item)

    def eventFilter(self, obj, event):
        if obj is not self.view.viewport():
            return False
        try:
            if event.type() == QEvent.MouseButtonPress and event.buttons() & Qt.LeftButton:
                self._draw_dot(event.pos())
                return True
            elif event.type() == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                self._draw_dot(event.pos())
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                return True
        except Exception as e:
            # 콘솔에만 경고 출력(앱 종료 방지)
            print(f"[WARN] paint error: {e}")
        return False


class SynchronizedZoomer:
    """
    두 개 이상의 QGraphicsView에 동일한 확대/축소를 적용.
    - current_scale은 fitInView 후의 '기준 배율' 대비 추가 배율을 나타냄.
    - reset_zoom_to_fit() 호출 시 기준 배율로 복귀.
    """
    def __init__(self, *views: QGraphicsView):
        self.views = list(views)
        self.min_scale = 0.10
        self.max_scale = 10.0
        self.current_scale = 1.0

        for v in self.views:
            # 보기 품질/동작 설정
            v.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            v.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            v.setResizeAnchor(QGraphicsView.AnchorViewCenter)
            if v.scene() is None:
                v.setScene(QGraphicsScene(v))

        # 시작 시 한 번 맞춰두면 좋다 (이미지가 있는 경우에만)
        # 초기화 시점에는 이미지가 없을 수 있으므로 show_photo에서 처리

    def _fit_one(self, v: QGraphicsView):
        sc = v.scene()
        if sc is None:
            return
        rect = sc.itemsBoundingRect()
        if rect.isValid():
            v.setTransform(QTransform())               # 기준 변환 초기화
            v.fitInView(rect, Qt.KeepAspectRatio)      # 보기 창에 꽉 차게(비율 유지)

    def reset_zoom_to_fit(self):
        for v in self.views:
            self._fit_one(v)
        self.current_scale = 1.0

    def _apply_scale(self, factor: float):
        # 현재 기준 대비 추가 배율을 factor만큼 곱한다.
        for v in self.views:
            v.scale(factor, factor)

    def zoom(self, direction: int):
        """
        direction: +1(확대), -1(축소)
        배율은 1.15 배수로 가감하고, 최소/최대 배율을 클램프.
        """
        step = 1.15 if direction > 0 else (1.0 / 1.15)
        new_scale = self.current_scale * step
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        factor = new_scale / self.current_scale
        if abs(factor - 1.0) < 1e-6:
            return
        self._apply_scale(factor)
        self.current_scale = new_scale


class PhotoViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_FILE), self)

        # === 왼쪽(real_photo) : 원본 ===
        self.scene = QtWidgets.QGraphicsScene(self)
        self.real_photo.setScene(self.scene)
        self.pixmap_item = None
        self.current_img = None

        # === 오른쪽(pixel_view) : 분류 결과 ===
        self.pixel_scene = QtWidgets.QGraphicsScene(self)
        self.pixel_view.setScene(self.pixel_scene)
        self.pixelmap_item = None

        # 1) QGraphicsView 2개를 컨트롤러에 등록
        self._views = [self.real_photo, self.pixel_view]
        self.zoomer = SynchronizedZoomer(*self._views)

        # 2) 안전장치: 씬이 없으면 생성
        for v in self._views:
            if v.scene() is None:
                v.setScene(QGraphicsScene(self))

        self.files = self._scan_files()
        self.index = 0

        # 버튼 연결
        self.clearButton.clicked.connect(self.clear_folder)
        # nextButton은 중앙에서 안전하게 처리 (페인터 clear + 줌 리셋)
        self.nextButton.clicked.connect(self._on_next_safely)
        self.saveButton.clicked.connect(self.confirm_colors)
        self.exitButton.clicked.connect(self.safe_exit)
        self.clearDataButton.clicked.connect(self.clear_data)

        # 3) 버튼 시그널 연결 (objectName: expansion / reduction / nextButton)
        # expansion/reduction 버튼이 있는 경우에만 연결
        if hasattr(self, 'expansion'):
            self.expansion.clicked.connect(self._on_zoom_in)
        if hasattr(self, 'reduction'):
            self.reduction.clicked.connect(self._on_zoom_out)

        # nextButton을 누르면 next_photo가 호출되고, 
        # show_photo에서 자동으로 줌 리셋이 실행됨

        # 주기적 갱신(신규 파일 감지)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_photos)
        self.timer.start(UI_UPDATE_INTERVAL)

        if self.files:
            self.show_photo(self.files[self.index])
        else:
            self._show_message("폴더가 비어 있습니다")

        # === 라디오버튼(product/background/defect)에 따른 브러시 색상 ===
        self._label_colors = {
            "product":    QtGui.QColor(40, 190, 80, 170),
            "background": QtGui.QColor(180, 180, 180, 170),
            "defect":     QtGui.QColor(250, 70, 70, 170),
        }
        def _current_color():
            prod = self.findChild(QtWidgets.QRadioButton, "product")
            back = self.findChild(QtWidgets.QRadioButton, "background")
            defe = self.findChild(QtWidgets.QRadioButton, "defect")
            if defe and defe.isChecked():
                return self._label_colors["defect"]
            if back and back.isChecked():
                return self._label_colors["background"]
            return self._label_colors["product"]

        # 두 QGraphicsView 객체 (이미 uic.loadUi로 로드됨)
        left_view = self.real_photo
        right_view = self.pixel_view

        # 페인터 장착 (둘 다; 필요하면 한쪽만 써도 됨)
        # auto_clear_on_next=False: 중앙에서 한 번만 처리하기 위해 자동 연결 끔
        if left_view:
            self.left_painter = SafeViewPainter(self, left_view, _current_color, radius=8, auto_clear_on_next=False)
        if right_view:
            self.right_painter = SafeViewPainter(self, right_view, _current_color, radius=8, auto_clear_on_next=False)

        # 드로잉 관련(왼쪽에서만 드래그 - 기존 RGB 수집 로직)
        self.drawing = False
        self.selected_points = []
        self.pending_colors = {}  # 임시 RGB 저장
        # 기존 eventFilter는 유지하되, 페인터와 충돌하지 않도록 함
        self.real_photo.viewport().installEventFilter(self)

        # main.py에서 주입 가능
        self.cap_proc = None

    # -------------------------------
    def _scan_files(self):
        PICTURE_DIR.mkdir(parents=True, exist_ok=True)
        return sorted(PICTURE_DIR.glob("frame_*.jpg"))

    def _show_message(self, text: str):
        self.scene.clear()
        self.scene.addText(text, QtGui.QFont("Arial", 14))

    # === 오른쪽 뷰 갱신 헬퍼 ===
    def update_pixel_view(self):
        if self.current_img is None:
            self.pixel_scene.clear()
            return
        pixel_map = make_pixel_map(self.current_img)
        pixmap2 = to_pixmap(pixel_map, QtGui)
        self.pixel_scene.clear()
        self.pixelmap_item = self.pixel_scene.addPixmap(pixmap2)
        # 줌 컨트롤러를 통해 fitInView 대신 reset_zoom_to_fit 사용
        # 단, 이미지가 업데이트된 후이므로 바로 리셋하면 안 됨
        # 대신 다음 이미지 로드 시 또는 resizeEvent에서 처리

    def show_photo(self, fpath: Path):
        img = cv2.imread(str(fpath))
        if img is None:
            self._show_message(f"이미지를 불러올 수 없습니다:\n{fpath.name}")
            return
        self.current_img = img

        # 왼쪽: 원본
        pixmap = to_pixmap(img, QtGui)
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.pixmap_item.setAcceptedMouseButtons(QtCore.Qt.NoButton)

        # 오른쪽: 분류 결과
        self.update_pixel_view()
        
        # 이미지 업데이트 후 줌 리셋은 _on_next_safely에서 처리
        # 초기 로드 시에만 리셋
        if not hasattr(self, '_initial_load_done'):
            QtCore.QTimer.singleShot(10, self.reset_zoom_to_fit)
            self._initial_load_done = True

    def _on_next_safely(self):
        """nextButton 클릭 시 안전하게 처리: 페인터 clear 후 다음 틱에서 줌 리셋"""
        # 1) 현재 남아있는 브러시/오버레이 안전 삭제
        if hasattr(self, 'left_painter'):
            self.left_painter.clear()
        if hasattr(self, 'right_painter'):
            self.right_painter.clear()
        # 2) 이미지 로드 (next_photo 호출)
        self.next_photo()
        # 3) 이미지가 교체될 시간을 한 틱 주고, 그 다음에 원배율로 맞춤
        QtCore.QTimer.singleShot(0, self.reset_zoom_to_fit)

    def next_photo(self):
        self.files = self._scan_files()
        if not self.files:
            self._show_message("폴더가 비어 있습니다")
            return
        self.index = (self.index + 1) % len(self.files)
        self.show_photo(self.files[self.index])

    def clear_folder(self):
        for f in PICTURE_DIR.glob("frame_*.jpg"):
            try:
                f.unlink()
            except Exception:
                pass
        self.files, self.index = [], 0
        self._show_message("폴더가 비어 있습니다")
        # 오른쪽도 초기화
        self.pixel_scene.clear()
        # 페인터 마크도 초기화
        if hasattr(self, 'left_painter'):
            self.left_painter.clear()
        if hasattr(self, 'right_painter'):
            self.right_painter.clear()

    def update_photos(self):
        new_files = self._scan_files()
        if new_files != self.files:
            self.files = new_files

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 리사이즈 시 줌 컨트롤러를 통해 리셋 (기준 배율 유지)
        if self._has_any_pixmap():
            QtCore.QTimer.singleShot(0, self.reset_zoom_to_fit)

    # ----------- Zoom Slots -----------
    def _on_zoom_in(self):
        try:
            if not self._has_any_pixmap():
                return
            self.zoomer.zoom(+1)
        except Exception as e:
            print(f"[WARN] zoom-in 실패: {e}")

    def _on_zoom_out(self):
        try:
            if not self._has_any_pixmap():
                return
            self.zoomer.zoom(-1)
        except Exception as e:
            print(f"[WARN] zoom-out 실패: {e}")

    def reset_zoom_to_fit(self):
        """다음 이미지로 넘어가거나 새 이미지를 표시한 직후 호출하면 원배율(기준배율)로 복귀."""
        try:
            self.zoomer.reset_zoom_to_fit()
        except Exception as e:
            print(f"[WARN] reset_zoom_to_fit 실패: {e}")

    def _has_any_pixmap(self) -> bool:
        """두 뷰 중 하나라도 PixmapItem이 있으면 True."""
        for v in self._views:
            sc = v.scene()
            if sc and any(isinstance(it, QGraphicsPixmapItem) for it in sc.items()):
                return True
        return False

    # -------------------------------
    def get_selected_label(self):
        if self.product.isChecked():
            return "product"
        elif self.defect.isChecked():
            return "defect"
        elif self.background.isChecked():
            return "background"
        return None

    def confirm_colors(self):
        """Save 버튼 → 임시 RGB를 Sphere로 등록하고 저장 + 오른쪽 즉시 갱신"""
        for label, rgb_set in self.pending_colors.items():
            if rgb_set:
                for rgb in rgb_set:
                    add_color_def(label, rgb, radius=SPHERE_RADIUS)
                print(f"[{label}] {len(rgb_set)}개 RGB → Sphere로 등록됨")
        self.pending_colors.clear()

        save_defs()
        print("color_defs.json에 저장 완료 ✅")

        # 오른쪽 뷰 즉시 갱신
        self.update_pixel_view()

    def clear_data(self):
        """Data Clear → JSON 초기화 + 오른쪽 즉시 갱신"""
        clear_defs()
        QtWidgets.QMessageBox.information(self, "Data Clear", "저장된 색상 정의가 모두 삭제되었습니다 ✅")
        self.update_pixel_view()

    def safe_exit(self):
        print("🔒 안전 종료 시작")
        save_defs()
        print("✅ 색상 정의 저장 완료")

        if self.cap_proc and self.cap_proc.poll() is None:
            self.cap_proc.terminate()
            print("📷 캡쳐 프로세스 종료")

        QtWidgets.QApplication.quit()

    # -------------------------------
    def eventFilter(self, source, event):
        if source == self.real_photo.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    self.drawing = True
                    self.selected_points = []
                    return True

            elif event.type() == QtCore.QEvent.MouseMove:
                if self.drawing and self.current_img is not None:
                    pos = self.real_photo.mapToScene(event.pos()).toPoint()
                    x, y = pos.x(), pos.y()
                    h, w = self.current_img.shape[:2]
                    if 0 <= x < w and 0 <= y < h:
                        self.selected_points.append((x, y))
                        overlay = draw_points(
                            self.current_img,
                            self.selected_points[-DRAW_POINT_LIMIT:],
                            radius=DRAW_POINT_RADIUS
                        )
                        pixmap = to_pixmap(overlay, QtGui)
                        self.scene.clear()
                        self.pixmap_item = self.scene.addPixmap(pixmap)
                    return True

            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if event.button() == QtCore.Qt.LeftButton and self.current_img is not None:
                    self.drawing = False
                    label = self.get_selected_label()
                    if not label:
                        print("라벨이 선택되지 않았습니다.")
                        return True

                    # 드래그 구간 RGB 수집
                    rgb_set = set()
                    img_rgb = cv2.cvtColor(self.current_img, cv2.COLOR_BGR2RGB)
                    for (x, y) in self.selected_points:
                        rgb_set.add(tuple(img_rgb[int(y), int(x)]))

                    if label not in self.pending_colors:
                        self.pending_colors[label] = set()
                    self.pending_colors[label].update(rgb_set)

                    print(f"[{label}] {len(rgb_set)}개 RGB 임시 저장됨")

                    # 왼쪽 하이라이트
                    overlay = highlight_rgb(self.current_img, rgb_set)
                    pixmap = to_pixmap(overlay, QtGui)
                    self.scene.clear()
                    self.pixmap_item = self.scene.addPixmap(pixmap)
                    return True
        return False
