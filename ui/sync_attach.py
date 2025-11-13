# ui/sync_attach.py
"""
이벤트 필터 기반 동기화 컨트롤러.
기존 QGraphicsView 위에 얹어서 왼쪽 색칠 → 오른쪽 실시간 동기화.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtCore import QObject, Qt, QPointF, QEvent
from PyQt5.QtGui import QImage, QPainter, QColor, QMouseEvent, QPixmap
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _scale_radius(r: int, lw: int, lh: int, rw: int, rh: int) -> int:
    # 좌/우 해상도 비율 평균으로 브러시 반경 스케일
    kx = rw / max(1, lw)
    ky = rh / max(1, lh)
    return max(1, int(round(r * (kx + ky) * 0.5)))


class _GVAdapter:
    """QGraphicsView 어댑터: 기존 scene/pixmap 위에 overlay를 얹어 브러시를 그린다."""
    def __init__(self, view: QGraphicsView):
        if view.scene() is None:
            # scene이 없으면 생성
            view.setScene(QGraphicsScene(view))
        self.view = view
        self.scene: QGraphicsScene = view.scene()

        # 기준(base) 픽스맵 아이템 추출(첫 번째 QGraphicsPixmapItem)
        base_item: Optional[QGraphicsPixmapItem] = None
        for it in self.scene.items():
            if isinstance(it, QGraphicsPixmapItem):
                base_item = it
                break
        if base_item is None:
            # 기준 픽스맵이 없으면 동작 불가
            raise RuntimeError("No QGraphicsPixmapItem found in scene of left/right view")

        self.base_item = base_item
        base_pm = self.base_item.pixmap()
        self.bw, self.bh = base_pm.width(), base_pm.height()

        # overlay 이미지 & 아이템(투명)
        self.overlay_img = QImage(self.bw, self.bh, QImage.Format_ARGB32_Premultiplied)
        self.overlay_img.fill(Qt.transparent)
        self.overlay_item = QGraphicsPixmapItem(QPixmap.fromImage(self.overlay_img))
        self.overlay_item.setZValue(self.base_item.zValue() + 10.0)
        self.overlay_item.setOpacity(0.55)
        self.overlay_item.setPos(self.base_item.pos())
        self.scene.addItem(self.overlay_item)

    def viewpos_to_imgxy(self, view_pos) -> Optional[Tuple[int, int]]:
        """뷰 좌표(QPointF) -> 기준 픽스맵(이미지) 좌표"""
        sp: QPointF = self.view.mapToScene(int(view_pos.x()), int(view_pos.y()))
        ip: QPointF = self.base_item.mapFromScene(sp)
        x, y = int(ip.x()), int(ip.y())
        if 0 <= x < self.bw and 0 <= y < self.bh:
            return x, y
        return None

    def paint_dot(self, x: int, y: int, radius: int, color: QColor):
        p = QPainter(self.overlay_img)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        d = radius * 2
        p.drawEllipse(x - radius, y - radius, d, d)
        p.end()
        self.overlay_item.setPixmap(QPixmap.fromImage(self.overlay_img))

    def image_size(self) -> Tuple[int, int]:
        return self.bw, self.bh


class ScribbleSyncFilter(QObject):
    """
    왼쪽 뷰에 설치하는 이벤트 필터.
    - 왼쪽에서 LeftDrag로 색칠하면: 왼쪽 overlay + 우측 overlay 동기화.
    - 확대/축소/스크롤은 QGraphicsView 변환으로 자동 보정.
    """
    def __init__(self, left_view: QGraphicsView, right_view: QGraphicsView,
                 brush_radius: int = 8, color: QColor = QColor(255, 0, 0, 220)):
        super().__init__(left_view)
        self.left = _GVAdapter(left_view)
        self.right = _GVAdapter(right_view)
        self.brush_r = max(1, int(brush_radius))
        self.color = color
        self.drawing = False

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:
        if ev.type() == QEvent.MouseButtonPress:
            mev: QMouseEvent = ev  # type: ignore
            if mev.button() == Qt.LeftButton:
                pos = mev.pos()  # PyQt5는 position() 없음
                imgxy = self.left.viewpos_to_imgxy(pos)
                if imgxy:
                    x, y = imgxy
                    self._paint_both(x, y)
                    self.drawing = True
                return True

        elif ev.type() == QEvent.MouseMove and self.drawing:
            mev: QMouseEvent = ev  # type: ignore
            pos = mev.pos()  # PyQt5는 position() 없음
            imgxy = self.left.viewpos_to_imgxy(pos)
            if imgxy:
                x, y = imgxy
                self._paint_both(x, y)
            return True

        elif ev.type() == QEvent.MouseButtonRelease:
            mev: QMouseEvent = ev  # type: ignore
            if mev.button() == Qt.LeftButton:
                self.drawing = False
                return True

        return False  # 나머지는 원래 처리로 전달

    def _paint_both(self, lx: int, ly: int):
        # 왼쪽에 그리기
        self.left.paint_dot(lx, ly, self.brush_r, self.color)
        # 좌표 매핑(해상도 비율)
        lw, lh = self.left.image_size()
        rw, rh = self.right.image_size()
        rx = _clamp(int(round(lx * rw / max(1, lw))), 0, rw-1)
        ry = _clamp(int(round(ly * rh / max(1, lh))), 0, rh-1)
        rr = _scale_radius(self.brush_r, lw, lh, rw, rh)
        self.right.paint_dot(rx, ry, rr, self.color)


def attach_sync(left_view: QGraphicsView, right_view: QGraphicsView,
                brush_radius: int = 8, color: QColor = QColor(255, 0, 0, 220)) -> ScribbleSyncFilter:
    """
    좌/우 QGraphicsView가 이미 존재하는 경우: 호출 한 줄로 동기화 활성화.
    """
    flt = ScribbleSyncFilter(left_view, right_view, brush_radius, color)
    left_view.installEventFilter(flt)
    return flt


def attach_sync_by_object_names(root: QWidget,
                                left_name: str,
                                right_name: str,
                                **kw) -> ScribbleSyncFilter:
    """
    객체 이름으로 위젯을 찾아 연결. (Qt Designer에서 objectName 설정되어 있을 때)
    """
    lv = root.findChild(QGraphicsView, left_name)
    rv = root.findChild(QGraphicsView, right_name)
    if not lv or not rv:
        raise RuntimeError(f"QGraphicsView not found: left_name={left_name}, right_name={right_name}")
    return attach_sync(lv, rv, **kw)


def attach_sync_auto(root: QWidget, **kw) -> ScribbleSyncFilter:
    """
    자동 탐지: 윈도우 하위에서 QGraphicsView 2개를 찾아 연결.
    - 이름에 'left'/'right'가 포함된 경우 우선 매칭.
    - 없으면 단순히 앞의 2개를 사용.
    """
    views = root.findChildren(QGraphicsView)
    if len(views) < 2:
        raise RuntimeError("Need at least two QGraphicsView widgets to attach sync")
    # 이름 힌트 기반 매칭
    left_candidates = [v for v in views if "left" in (v.objectName() or "").lower() or "real" in (v.objectName() or "").lower()]
    right_candidates = [v for v in views if "right" in (v.objectName() or "").lower() or "pixel" in (v.objectName() or "").lower()]
    if left_candidates and right_candidates:
        lv, rv = left_candidates[0], right_candidates[0]
    else:
        # 첫 두 개 사용
        lv, rv = views[0], views[1]
    return attach_sync(lv, rv, **kw)

