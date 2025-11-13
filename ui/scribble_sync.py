# ui/scribble_sync.py

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem


def qimage_from_path(path: str) -> QImage:
    img = QImage(path)
    if img.isNull():
        raise FileNotFoundError(f"Image not found or invalid: {path}")
    return img.convertToFormat(QImage.Format_ARGB32)


class ScribbleView(QGraphicsView):
    """
    좌측/우측 어느 쪽에도 쓸 수 있는 공용 뷰.
    - base_img: 표시 기준 이미지(QImage)
    - overlay_img: 스크리블을 누적하는 투명 레이어(ARGB32)
    - pixmap_item: base_img 표시용
    - overlay_item: overlay_img 표시용(반투명)
    """
    def __init__(self, base_img: QImage, parent=None):
        super().__init__(parent)
        self.setRenderHints(self.renderHints() | 
                            QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        self.base_img = base_img
        self.overlay_img = QImage(base_img.size(), QImage.Format_ARGB32_Premultiplied)
        self.overlay_img.fill(Qt.transparent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem(QPixmap.fromImage(self.base_img))
        self.overlay_item = QGraphicsPixmapItem(QPixmap.fromImage(self.overlay_img))
        self.overlay_item.setOpacity(0.55)

        self.scene.addItem(self.pixmap_item)
        self.scene.addItem(self.overlay_item)

        self.setMouseTracking(True)
        self._drawing = False

        # 브러시 기본값
        self.brush_radius = 8
        self.brush_color = QColor(255, 0, 0, 220)  # 반투명 빨강

        # 동기화 상대
        self.partner: Optional["ScribbleView"] = None

        # 보기 설정(이미지 전체가 보이도록)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    # ---------- 좌표 변환: view -> image ----------
    def view_to_image_xy(self, view_pos) -> Optional[tuple[int, int]]:
        """뷰 좌표(event.pos)를 이미지 픽셀 좌표로 변환."""
        scene_pt: QPointF = self.mapToScene(int(view_pos.x()), int(view_pos.y()))
        item_pt: QPointF = self.pixmap_item.mapFromScene(scene_pt)  # 이미지 좌표계
        x, y = int(item_pt.x()), int(item_pt.y())
        if 0 <= x < self.base_img.width() and 0 <= y < self.base_img.height():
            return x, y
        return None

    # ---------- 페인트 ----------
    def paint_dot_on_overlay(self, x: int, y: int, radius: int, color: QColor):
        p = QPainter(self.overlay_img)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        d = radius * 2
        p.drawEllipse(x - radius, y - radius, d, d)
        p.end()
        self.overlay_item.setPixmap(QPixmap.fromImage(self.overlay_img))

    def scaled_brush_radius_for_partner(self, partner: "ScribbleView", r: int) -> int:
        # 좌표 매핑 스케일(원본 기준)
        sx = partner.base_img.width()  / self.base_img.width()
        sy = partner.base_img.height() / self.base_img.height()
        # 원형 브러시의 체감 반경 스케일은 평균 사용(너무 작아지지 않도록 하한 1)
        return max(1, int(round(r * (sx + sy) * 0.5)))

    # ---------- 동기화 ----------
    def set_partner(self, partner: "ScribbleView"):
        self.partner = partner

    def sync_paint_to_partner(self, x_img: int, y_img: int, base_radius: int, color: QColor):
        if not self.partner:
            return
        # 좌측 이미지 좌표 -> 우측 이미지 좌표(해상도 기반 1:1 매핑)
        rx = int(round(x_img * self.partner.base_img.width()  / self.base_img.width()))
        ry = int(round(y_img * self.partner.base_img.height() / self.base_img.height()))
        r2 = self.scaled_brush_radius_for_partner(self.partner, base_radius)
        # 파트너 이미지 경계 클리핑
        rx = max(0, min(rx, self.partner.base_img.width()  - 1))
        ry = max(0, min(ry, self.partner.base_img.height() - 1))
        self.partner.paint_dot_on_overlay(rx, ry, r2, color)

    # ---------- 마우스 이벤트 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drawing = True
            pos = self.view_to_image_xy(e.pos())
            if pos:
                x, y = pos
                self.paint_dot_on_overlay(x, y, self.brush_radius, self.brush_color)
                self.sync_paint_to_partner(x, y, self.brush_radius, self.brush_color)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drawing:
            pos = self.view_to_image_xy(e.pos())
            if pos:
                x, y = pos
                self.paint_dot_on_overlay(x, y, self.brush_radius, self.brush_color)
                self.sync_paint_to_partner(x, y, self.brush_radius, self.brush_color)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drawing = False
        super().mouseReleaseEvent(e)

    # ---------- API ----------
    def set_brush(self, radius: int, color: Optional[QColor] = None):
        self.brush_radius = int(max(1, radius))
        if color is not None:
            self.brush_color = color

    def clear_overlay(self):
        self.overlay_img.fill(Qt.transparent)
        self.overlay_item.setPixmap(QPixmap.fromImage(self.overlay_img))


def link_views(left: ScribbleView, right: ScribbleView):
    """좌우 뷰를 동기화 연결."""
    left.set_partner(right)
    right.set_partner(left)

