# ui/demo_scribble_sync_qt.py

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from ui.scribble_sync import ScribbleView, qimage_from_path, link_views


LEFT_PATH = os.environ.get("LEFT_IMG", "left.jpg")    # 필요 시 env로 경로 지정
RIGHT_PATH = os.environ.get("RIGHT_IMG", "right.jpg") # 없으면 left를 축소해 사용


def main():
    app = QApplication(sys.argv)

    # 이미지 로드
    left_img = qimage_from_path(LEFT_PATH)

    if os.path.exists(RIGHT_PATH):
        right_img = qimage_from_path(RIGHT_PATH)
    else:
        # 오른쪽을 픽셀화(축소)한 버전으로 생성
        right_img = left_img.scaled(left_img.width()//4, left_img.height()//4,
                                    Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # 뷰 구성
    left_view  = ScribbleView(left_img)
    right_view = ScribbleView(right_img)
    left_view.setWindowTitle("LEFT: original")
    right_view.setWindowTitle("RIGHT: pixelized")

    # 동기화 링크
    link_views(left_view, right_view)

    # UI 배치
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(6,6,6,6)
    lay.addWidget(left_view, 1)
    lay.addWidget(right_view, 1)
    w.setWindowTitle("Scribble Sync Demo (Left → Right)")
    w.resize(1200, 700)
    w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

