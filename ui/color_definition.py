from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import Qt, QPointF
import cv2
import os

from package.image_utils import to_pixmap, draw_points, highlight_rgb, make_pixel_map
from package.color_utils import add_color_def, save_defs, clear_defs
from package.operation import (
    DRAW_POINT_RADIUS, DRAW_POINT_LIMIT, UI_UPDATE_INTERVAL,
    SPHERE_RADIUS, PICTURE_DIR
)

UI_FILE = Path(__file__).resolve().with_name("mainwindow.ui")


class _Overlay:
    """각 QGraphicsView 위에 반투명 마스크(QImage)를 얹어 그림."""
    def __init__(self, view: QGraphicsView):
        self.view = view
        if self.view.scene() is None:
            self.view.setScene(QGraphicsScene(self.view))
        self.overlay_item = QGraphicsPixmapItem()
        self.overlay_item.setZValue(1000)  # 맨 위
        self.view.scene().addItem(self.overlay_item)
        self.img = None  # QImage(ARGB32)
        self._last_base_rect = None

    def ensure_size_from_base(self) -> bool:
        """씬에 있는 가장 큰 PixmapItem을 찾아 그 크기로 오버레이 초기화."""
        sc = self.view.scene()
        base_items = [it for it in sc.items() if isinstance(it, QGraphicsPixmapItem) and it is not self.overlay_item]
        if not base_items:
            return False
        # 가장 큰 영역을 가진 픽스맵을 기준으로
        base = max(base_items, key=lambda it: it.pixmap().width() * it.pixmap().height())
        pm = base.pixmap()
        if pm.isNull():
            return False
        if (self.img is None) or (self.img.width() != pm.width()) or (self.img.height() != pm.height()):
            self.img = QtGui.QImage(pm.width(), pm.height(), QtGui.QImage.Format_ARGB32_Premultiplied)
            self.img.fill(Qt.transparent)
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.img))
        self._last_base_rect = base.sceneBoundingRect()
        return True

    def scene_to_local(self, scene_pos: QPointF) -> QtCore.QPoint:
        """씬 좌표 → 오버레이 로컬 픽셀 좌표로 변환."""
        if self._last_base_rect is None:
            return QtCore.QPoint(-1, -1)
        x = int(scene_pos.x() - self._last_base_rect.left())
        y = int(scene_pos.y() - self._last_base_rect.top())
        return QtCore.QPoint(x, y)

    def paint_dot(self, local_pt: QtCore.QPoint, radius: int, color: QtGui.QColor):
        if self.img is None:
            return
        if not (0 <= local_pt.x() < self.img.width() and 0 <= local_pt.y() < self.img.height()):
            return
        p = QtGui.QPainter(self.img)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QBrush(color))
        p.drawEllipse(local_pt, radius, radius)
        p.end()
        self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.img))

    def clear(self):
        if self.img is not None:
            self.img.fill(Qt.transparent)
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.img))


class DualPainter(QtCore.QObject):
    """
    두 개 QGraphicsView(real_photo, pixel_view)에서 동일 로직으로 칠하기.
    - 좌클릭 드래그로 브러시 페인트
    - 뷰 확대/축소와 공존 (페인트 중에는 팬 비활성)
    """
    def __init__(self, left_view: QGraphicsView, right_view: QGraphicsView,
                 color_getter, radius: int = 8, parent=None):
        super().__init__(parent)
        self.left = _Overlay(left_view)
        self.right = _Overlay(right_view)
        self.color_getter = color_getter
        self.radius = radius
        self._painting = False
        self._saved_dragmode = {
            left_view: left_view.dragMode(),
            right_view: right_view.dragMode()
        }

        # 이벤트 필터 장착
        left_view.installEventFilter(self)
        right_view.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if isinstance(obj, QGraphicsView):
            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                self._painting = True
                obj.setDragMode(QGraphicsView.NoDrag)  # 그리는 동안 팬 잠시 off
                self._paint_once(obj, ev.pos())
                return True
            if ev.type() == QtCore.QEvent.MouseMove and self._painting:
                self._paint_once(obj, ev.pos())
                return True
            if ev.type() == QtCore.QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                self._painting = False
                # 원래 드래그 모드 복원(보통 ScrollHandDrag)
                orig = self._saved_dragmode.get(obj, QGraphicsView.ScrollHandDrag)
                obj.setDragMode(orig)
                return True
        return super().eventFilter(obj, ev)

    def _paint_once(self, view: QGraphicsView, view_pos: QtCore.QPoint):
        color = self.color_getter()  # UI 라디오버튼 상태 기반 색상
        overlay = self.left if view is self.left.view else self.right
        if not overlay.ensure_size_from_base():
            return
        scene_pos = view.mapToScene(view_pos)
        local_pt = overlay.scene_to_local(scene_pos)
        overlay.paint_dot(local_pt, self.radius, color)

    def clear_both(self):
        self.left.clear()
        self.right.clear()

    def set_radius(self, r: int):
        self.radius = max(1, int(r))


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
        self.nextButton.clicked.connect(self.next_photo)
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
        def _current_color():
            if getattr(self, "product", None) and self.product.isChecked():
                return QtGui.QColor(0, 200, 0, 160)        # product = Green
            if getattr(self, "background", None) and self.background.isChecked():
                return QtGui.QColor(0, 140, 255, 160)     # background = Blue
            if getattr(self, "defect", None) and self.defect.isChecked():
                return QtGui.QColor(255, 60, 60, 160)     # defect = Red
            return QtGui.QColor(255, 200, 0, 160)         # fallback (yellow)

        # === 두 뷰(왼쪽 real_photo, 오른쪽 pixel_view)에 동시에 적용 가능한 페인터 생성 ===
        self.painter = DualPainter(self.real_photo, self.pixel_view, color_getter=_current_color, radius=10, parent=self)

        # (선택) 브러시 크기 조절을 핫키로: Ctrl + 휠
        self._original_left_wheel = self.real_photo.wheelEvent
        self._original_right_wheel = self.pixel_view.wheelEvent
        self.real_photo.wheelEvent = self._wrap_wheel(self._original_left_wheel)
        self.pixel_view.wheelEvent = self._wrap_wheel(self._original_right_wheel)

        # 다음 버튼 누를 때 오버레이도 같이 초기화(줌 리셋과 병행 연결 가능)
        self.nextButton.clicked.connect(self.painter.clear_both)

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
        
        # 이미지 업데이트 후 줌 리셋 (원배율로 표시)
        # nextButton 클릭 시 또는 초기 로드 시에만 리셋되도록 함
        QtCore.QTimer.singleShot(10, self.reset_zoom_to_fit)

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

    def _wrap_wheel(self, base_wheel):
        # Ctrl + 휠로 브러시 반경 조절 (기존 휠 줌은 그대로 두되, Ctrl일 때만 가로챔)
        def handler(ev: QtGui.QWheelEvent):
            if ev.modifiers() & Qt.ControlModifier:
                delta = ev.angleDelta().y()
                self.painter.set_radius(self.painter.radius + (2 if delta > 0 else -2))
                ev.accept()
            else:
                base_wheel(ev)
        return handler

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
