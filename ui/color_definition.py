from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore, uic
import cv2

from package.image_utils import to_pixmap, draw_points, highlight_rgb, make_pixel_map
from package.color_utils import add_color_def, save_defs, clear_defs
from package.operation import (
    DRAW_POINT_RADIUS, DRAW_POINT_LIMIT, UI_UPDATE_INTERVAL,
    SPHERE_RADIUS, PICTURE_DIR
)

UI_FILE = Path(__file__).resolve().with_name("mainwindow.ui")


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
        self.current_pixel_map = None  # 현재 픽셀맵 저장 (우측 동기화용)

        self.files = self._scan_files()
        self.index = 0

        # 버튼 연결
        self.clearButton.clicked.connect(self.clear_folder)
        self.nextButton.clicked.connect(self.next_photo)
        self.saveButton.clicked.connect(self.confirm_colors)
        self.exitButton.clicked.connect(self.safe_exit)
        self.clearDataButton.clicked.connect(self.clear_data)

        # 주기적 갱신(신규 파일 감지)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_photos)
        self.timer.start(UI_UPDATE_INTERVAL)

        if self.files:
            self.show_photo(self.files[self.index])
        else:
            self._show_message("폴더가 비어 있습니다")

        # 드로잉 관련(왼쪽에서만 드래그)
        self.drawing = False
        self.selected_points = []
        self.pending_colors = {}  # 임시 RGB 저장
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
        self.pixel_view.fitInView(self.pixelmap_item, QtCore.Qt.KeepAspectRatio)

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
        self.real_photo.fitInView(self.pixmap_item, QtCore.Qt.KeepAspectRatio)

        # 오른쪽: 분류 결과
        self.update_pixel_view()

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
        if self.files and self.pixmap_item:
            self.real_photo.fitInView(self.pixmap_item, QtCore.Qt.KeepAspectRatio)
        if self.pixelmap_item:
            self.pixel_view.fitInView(self.pixelmap_item, QtCore.Qt.KeepAspectRatio)

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
