from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import Qt, QPointF, QEvent
import cv2
import os
import datetime
import numpy as np
import sip  # PyQt5에서 객체 삭제 여부 확인용

from package.image_utils import to_pixmap, draw_points, highlight_rgb, make_pixel_map
from package.color_utils import add_color_def, save_defs, clear_defs
from package.operation import (
    DRAW_POINT_RADIUS, DRAW_POINT_LIMIT, UI_UPDATE_INTERVAL,
    SPHERE_RADIUS, PICTURE_DIR
)

UI_FILE = Path(__file__).resolve().with_name("mainwindow.ui")

# 라벨 색 (오른쪽 픽셀 뷰 재색칠에 사용)
LABEL_COLORS = {
    1: QtGui.QColor(0, 200, 0, 160),      # product = 초록
    2: QtGui.QColor(0, 140, 255, 160),    # background = 파랑
    3: QtGui.QColor(255, 60, 60, 160),    # defect = 빨강
}

# 같은 RGB값 하이라이트 색
MATCH_HINT_COLOR = QtGui.QColor(255, 255, 0, 120)  # 노랑

# 동일 기준 허용 오차 (픽셀화에서는 0으로도 충분, 실사쪽은 0~3 정도 권장)
MATCH_TOL = 0


def _largest_pixmap_item(scene: QtWidgets.QGraphicsScene):
    """씬에서 가장 큰 PixmapItem을 찾아 반환 (안전하게)."""
    if scene is None:
        return None
    base = None
    base_area = -1
    for it in scene.items():
        if not isinstance(it, QGraphicsPixmapItem):
            continue
        if sip.isdeleted(it):
            continue
        try:
            pm = it.pixmap()
            if pm.isNull():
                continue
            area = pm.width() * pm.height()
            if area > base_area:
                base = it
                base_area = area
        except Exception:
            continue
    return base


class OverlayMask:
    """
    각 QGraphicsView 위에 반투명 오버레이(QImage) + 정수 라벨마스크(np.ndarray)를 유지.
    - view.scene()의 '기저 픽스맵' 크기에 맞춰 자동 리크리에이트
    - scene이 교체돼도 overlay_item을 재부착하여 안전
    - 라벨용 오버레이와 하이라이트용 오버레이를 분리
    """
    def __init__(self, view: QGraphicsView):
        self.view = view
        if self.view.scene() is None:
            self.view.setScene(QGraphicsScene(self.view))

        # 라벨용 오버레이
        self.overlay_item = QGraphicsPixmapItem()
        self.overlay_item.setZValue(1000)

        # 하이라이트(같은 RGB 표시) 오버레이
        self.hint_item = QGraphicsPixmapItem()
        self.hint_item.setZValue(1001)

        self._base_rect = None
        self.qimage = None          # 라벨 그리기용
        self.hint_qimage = None     # 동일 RGB 하이라이트용
        self.mask_idx = None        # (H,W) uint8 라벨맵 (0=미지정, 1/2/3...)

        self._ensure_binding()

    def _ensure_binding(self):
        # 씬 보장 및 아이템 재부착
        if self.view.scene() is None:
            self.view.setScene(QGraphicsScene(self.view))
        sc = self.view.scene()

        for attr in ("overlay_item", "hint_item"):
            item = getattr(self, attr)
            # 삭제되었으면 재생성
            if item is None or sip.isdeleted(item):
                item = QGraphicsPixmapItem()
                setattr(self, attr, item)
                item.setZValue(1000 if attr == "overlay_item" else 1001)

            # 현재 씬에 부착
            cur = None
            try:
                cur = item.scene()
            except Exception:
                cur = None

            if cur is not sc:
                if cur is not None:
                    try:
                        cur.removeItem(item)
                    except Exception:
                        pass
                if sc is not None:
                    sc.addItem(item)

        # 기존 QImage가 있으면 다시 세팅
        if self.qimage is not None and not self.qimage.isNull():
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.qimage))
        if self.hint_qimage is not None and not self.hint_qimage.isNull():
            self.hint_item.setPixmap(QtGui.QPixmap.fromImage(self.hint_qimage))

    def _find_base(self):
        """기저 픽스맵 아이템 찾기."""
        return _largest_pixmap_item(self.view.scene())

    def ensure_from_base(self) -> bool:
        """기저 픽스맵 크기에 맞춰 qimage/mask를 보장."""
        self._ensure_binding()
        base = self._find_base()
        if base is None:
            return False
        try:
            pm = base.pixmap()
        except Exception:
            return False
        if pm.isNull():
            return False

        need_new = (
            self.qimage is None or
            self.qimage.width() != pm.width() or
            self.qimage.height() != pm.height()
        )
        if need_new:
            w, h = pm.width(), pm.height()
            # 라벨 QImage
            self.qimage = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32_Premultiplied)
            self.qimage.fill(Qt.transparent)
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.qimage))
            # 힌트 QImage
            self.hint_qimage = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32_Premultiplied)
            self.hint_qimage.fill(Qt.transparent)
            self.hint_item.setPixmap(QtGui.QPixmap.fromImage(self.hint_qimage))
            # 라벨맵
            self.mask_idx = np.zeros((h, w), dtype=np.uint8)

        # 좌표 변환용 SceneRect
        try:
            self._base_rect = base.sceneBoundingRect()
        except Exception:
            return False
        return True

    @property
    def base_size(self):
        if self.qimage is None:
            return None
        return (self.qimage.width(), self.qimage.height())

    def scene_to_local(self, scene_pos: QPointF) -> QtCore.QPoint:
        """씬 좌표 → 기저 픽스맵 로컬 픽셀 좌표."""
        if self._base_rect is None:
            return QtCore.QPoint(-1, -1)
        x = int(scene_pos.x() - self._base_rect.left())
        y = int(scene_pos.y() - self._base_rect.top())
        return QtCore.QPoint(x, y)

    def paint_disk(self, local_pt: QtCore.QPoint, radius: int, color: QtGui.QColor, label_idx: int):
        """라벨 그리기(마스크도 함께)."""
        if self.qimage is None or self.mask_idx is None:
            return
        h, w = self.mask_idx.shape
        if not (0 <= local_pt.x() < w and 0 <= local_pt.y() < h):
            return

        # 라벨 오버레이
        try:
            p = QtGui.QPainter(self.qimage)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QBrush(color))
            p.drawEllipse(local_pt, radius, radius)
            p.end()
            self._ensure_binding()
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.qimage))
        except Exception:
            return

        # 라벨맵
        cv2.circle(self.mask_idx, (local_pt.x(), local_pt.y()), int(radius), int(label_idx), thickness=-1)

    def show_match_hint(self, mask_bool: np.ndarray, color: QtGui.QColor = MATCH_HINT_COLOR):
        """mask_bool(H,W)==True인 위치를 색으로 칠해 힌트 레이어에 표시 (라벨맵에는 영향 없음)."""
        if self.hint_qimage is None:
            return
        h, w = mask_bool.shape
        if h != self.hint_qimage.height() or w != self.hint_qimage.width():
            return
        # RGBA 배열 만들기
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        arr[mask_bool] = [color.red(), color.green(), color.blue(), color.alpha()]
        qimg = QtGui.QImage(arr.data, w, h, 4*w, QtGui.QImage.Format_RGBA8888)
        self.hint_qimage = qimg.copy()
        self._ensure_binding()
        self.hint_item.setPixmap(QtGui.QPixmap.fromImage(self.hint_qimage))

    def clear_hint(self):
        """하이라이트만 지우기."""
        if self.hint_qimage is not None:
            self.hint_qimage.fill(Qt.transparent)
            self._ensure_binding()
            self.hint_item.setPixmap(QtGui.QPixmap.fromImage(self.hint_qimage))

    def recolor_from_labelmap(self, mapping: dict):
        """mask_idx를 이용해 라벨별 색으로 라벨 오버레이를 다시 만든다."""
        if self.mask_idx is None or self.qimage is None:
            return
        h, w = self.mask_idx.shape
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        for idx, qcol in mapping.items():
            m = (self.mask_idx == idx)
            if not m.any():
                continue
            arr[m] = [qcol.red(), qcol.green(), qcol.blue(), qcol.alpha()]
        qimg = QtGui.QImage(arr.data, w, h, 4*w, QtGui.QImage.Format_RGBA8888)
        self.qimage = qimg.copy()
        self._ensure_binding()
        self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.qimage))

    def clear_all(self):
        """전체 리셋(다음 이미지 대비)."""
        if self.qimage is not None:
            self.qimage.fill(Qt.transparent)
            self._ensure_binding()
            self.overlay_item.setPixmap(QtGui.QPixmap.fromImage(self.qimage))
        if self.hint_qimage is not None:
            self.hint_qimage.fill(Qt.transparent)
            self._ensure_binding()
            self.hint_item.setPixmap(QtGui.QPixmap.fromImage(self.hint_qimage))
        if self.mask_idx is not None:
            self.mask_idx[:] = 0


class LinkedDualPainter(QtCore.QObject):
    """
    좌/우 두 뷰가 서로 '정규화 좌표'로 동기화 페인팅:
    - 한쪽에 칠하면 다른 쪽에도 동일 위치로 즉시 반영
    - 저장 시 두 마스크를 PNG/NPY로 기록
    - 같은 RGB 값 하이라이트 기능
    - 저장 시 오른쪽 픽셀 뷰 재색칠 기능
    """
    def __init__(self, root: QtWidgets.QWidget, left: QGraphicsView, right: QGraphicsView,
                 label_selector, radius: int = 8):
        super().__init__(root)
        self.root = root
        self.left = left
        self.right = right
        self.ovL = OverlayMask(left)
        self.ovR = OverlayMask(right)
        self.label_selector = label_selector
        self.radius = max(1, int(radius))
        self._painting = False
        self._in_reset = False

        # 이벤트 필터는 viewport에 단다(정확한 마우스 좌표 확보)
        self.left.viewport().installEventFilter(self)
        self.right.viewport().installEventFilter(self)

        # 보기 품질/앵커
        for v in (self.left, self.right):
            v.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            v.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            v.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # 버튼 연결
        nb = root.findChild(QtWidgets.QPushButton, "nextButton")
        if nb:
            nb.clicked.connect(self._queue_reset)   # 다음에서 안전 초기화
        clr = root.findChild(QtWidgets.QPushButton, "clearDataButton")
        if clr:
            clr.clicked.connect(self.clear_both)
        sv = root.findChild(QtWidgets.QPushButton, "saveButton")
        if sv:
            sv.clicked.connect(self.save_masks_and_recolor_right)

    # ---------- 내부 유틸 ----------
    def _ensure_ready(self):
        if self._in_reset:
            return False
        return (self.ovL.ensure_from_base() and self.ovR.ensure_from_base())

    def _qimage_to_rgb_array(self, pm: QtGui.QPixmap) -> np.ndarray:
        """QPixmap -> RGB ndarray(H,W,3)"""
        qimg = pm.toImage().convertToFormat(QtGui.QImage.Format_RGB888)
        h, w = qimg.height(), qimg.width()
        ptr = qimg.bits()
        ptr.setsize(h * w * 3)
        arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 3)).copy()
        return arr

    def _right_base_rgb(self):
        """오른쪽 픽셀화 뷰의 베이스 이미지를 RGB ndarray로 가져오기"""
        rpmi = _largest_pixmap_item(self.right.scene())
        if rpmi is None:
            return None
        try:
            pm = rpmi.pixmap()
        except Exception:
            return None
        if pm.isNull():
            return None
        return self._qimage_to_rgb_array(pm)

    def _make_match_mask_on_right(self, rgb: np.ndarray, tol: int = MATCH_TOL):
        """오른쪽 베이스 이미지에서 rgb(1x3)와 같은(±tol) 위치를 True로."""
        arr = self._right_base_rgb()
        if arr is None:
            return None
        if tol <= 0:
            mask = np.all(arr == rgb[None, None, :], axis=2)
        else:
            mask = np.all(np.abs(arr.astype(np.int16) - rgb[None, None, :].astype(np.int16)) <= tol, axis=2)
        return mask

    def _color_at_left(self, x: int, y: int):
        """왼쪽 베이스 이미지에서 (x,y) 위치의 RGB 값 가져오기"""
        lpmi = _largest_pixmap_item(self.left.scene())
        if lpmi is None:
            return None
        try:
            pm = lpmi.pixmap()
        except Exception:
            return None
        if pm.isNull():
            return None
        arr = self._qimage_to_rgb_array(pm)
        if 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
            return arr[y, x].copy()   # shape (3,)
        return None

    def _paint_pair(self, side: str, view_pos: QtCore.QPoint):
        if not self._ensure_ready():
            return
        label_idx, color = self.label_selector()

        if side == "left":
            # 좌측 라벨 페인트 + 우측 동기
            scene_pt = self.left.mapToScene(view_pos)
            lpt = self.ovL.scene_to_local(scene_pt)
            self.ovL.paint_disk(lpt, self.radius, LABEL_COLORS.get(label_idx, color), label_idx)

            # 좌 -> 우 정규화 매핑
            szL = self.ovL.base_size
            szR = self.ovR.base_size
            if szL and szR:
                lx, ly = lpt.x(), lpt.y()
                rx = int(round(lx * (szR[0]/float(szL[0]))))
                ry = int(round(ly * (szR[1]/float(szL[1]))))
                self.ovR.paint_disk(QtCore.QPoint(rx, ry), self.radius, LABEL_COLORS.get(label_idx, color), label_idx)

            # === 같은 RGB값 하이라이트 (좌측 픽셀의 RGB 기준으로 우측에 표시) ===
            rgb = self._color_at_left(lpt.x(), lpt.y())
            if rgb is not None:
                mask = self._make_match_mask_on_right(rgb, MATCH_TOL)
                if mask is not None:
                    self.ovR.show_match_hint(mask, MATCH_HINT_COLOR)

        else:
            # 우측 라벨 페인트 + 좌측 동기
            scene_pt = self.right.mapToScene(view_pos)
            rpt = self.ovR.scene_to_local(scene_pt)
            self.ovR.paint_disk(rpt, self.radius, LABEL_COLORS.get(label_idx, color), label_idx)

            # 우 -> 좌 정규화 매핑
            szL = self.ovL.base_size
            szR = self.ovR.base_size
            if szL and szR:
                rx, ry = rpt.x(), rpt.y()
                lx = int(round(rx * (szL[0]/float(szR[0]))))
                ly = int(round(ry * (szL[1]/float(szR[1]))))
                self.ovL.paint_disk(QtCore.QPoint(lx, ly), self.radius, LABEL_COLORS.get(label_idx, color), label_idx)

            # (옵션) 우측에서 찍은 RGB를 기준으로도 하이라이트 가능
            rb = self._right_base_rgb()
            if rb is not None and 0 <= rpt.y() < rb.shape[0] and 0 <= rpt.x() < rb.shape[1]:
                rgb = rb[rpt.y(), rpt.x()].copy()
                mask = self._make_match_mask_on_right(rgb, MATCH_TOL)
                if mask is not None:
                    self.ovR.show_match_hint(mask, MATCH_HINT_COLOR)

    # ---------- 이벤트 처리 ----------
    def eventFilter(self, obj, ev):
        if self._in_reset:
            return False
        try:
            is_left = (obj is self.left.viewport())
            is_right = (obj is self.right.viewport())
            if not (is_left or is_right):
                return False

            if ev.type() == QEvent.MouseButtonPress and ev.buttons() & Qt.LeftButton:
                self._painting = True
                self._paint_pair("left" if is_left else "right", ev.pos())
                return True
            elif ev.type() == QEvent.MouseMove and self._painting and ev.buttons() & Qt.LeftButton:
                self._paint_pair("left" if is_left else "right", ev.pos())
                return True
            elif ev.type() == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                self._painting = False
                return True
        except Exception as e:
            print(f"[WARN] paint error: {e}")
        return False

    # ---------- 유틸 ----------
    def clear_both(self):
        self.ovL.clear()
        self.ovR.clear()

    def on_next(self):
        # 다른 슬롯(이미지 교체)이 끝난 뒤 초기화되도록 다음 틱에 실행
        QtCore.QTimer.singleShot(0, self.clear_both)

    def save_masks(self):
        """두 마스크를 PNG/NPY로 저장(라벨 인덱스: 0=none, 1=product, 2=background, 3=defect)."""
        if self.ovL.mask_idx is None or self.ovR.mask_idx is None:
            print("[INFO] 저장할 마스크가 없습니다.")
            return
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "labels")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # PNG (가시용) & NPY (학습/후처리용)
        cv2.imwrite(os.path.join(out_dir, f"left_mask_{ts}.png"), self.ovL.mask_idx)
        cv2.imwrite(os.path.join(out_dir, f"right_mask_{ts}.png"), self.ovR.mask_idx)
        np.save(os.path.join(out_dir, f"left_mask_{ts}.npy"), self.ovL.mask_idx)
        np.save(os.path.join(out_dir, f"right_mask_{ts}.npy"), self.ovR.mask_idx)

        print(f"[SAVED] {out_dir} 에 마스크 저장 완료: left/right_mask_{ts}.*")


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

        # === 라디오버튼(product/background/defect)에 따른 라벨 인덱스 & 표색 ===
        self._label_color = {
            1: QtGui.QColor(40, 190, 80, 170),   # product
            2: QtGui.QColor(60, 160, 255, 170),  # background
            3: QtGui.QColor(250, 70, 70, 170),   # defect
        }
        def label_selector():
            if self.defect.isChecked():
                return 3, self._label_color[3]
            if self.background.isChecked():
                return 2, self._label_color[2]
            return 1, self._label_color[1]  # product 기본

        # 두 QGraphicsView (objectName 기준)
        left_view = self.real_photo
        right_view = self.pixel_view

        # 동기 페인터 장착: 좌↔우 상호 연동 + 저장 버튼 연결 + next 안전 초기화
        self.linked_painter = LinkedDualPainter(self, left_view, right_view, label_selector, radius=10)

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
        """nextButton 클릭 시 안전하게 처리: 페인터 clear는 linked_painter.on_next에서 처리"""
        # 1) 이미지 로드 (next_photo 호출)
        self.next_photo()
        # 2) 이미지가 교체될 시간을 한 틱 주고, 그 다음에 원배율로 맞춤
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
        if hasattr(self, 'linked_painter'):
            self.linked_painter.clear_both()

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
