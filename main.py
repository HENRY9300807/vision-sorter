import sys
import os
import subprocess
from PyQt5 import QtWidgets

# UI 클래스
from ui.color_definition import PhotoViewer
# 🎯 색상 정의 불러오기/저장
from package.color_utils import load_defs, save_defs


if __name__ == "__main__":
    # ── 실행 시 색상 정의 불러오기
    load_defs()

    # ── 백그라운드 스크립트 실행
    base_dir = os.path.dirname(__file__)
    script_path1 = os.path.join(base_dir, "package", "capture_96_limit.py")

    cap_proc = None
    try:
        cap_proc = subprocess.Popen([sys.executable, script_path1])
    except Exception as e:
        print(f"⚠️ 캡쳐 프로세스 실행 실패: {e}")

    # ── PyQt 앱 실행
    app = QtWidgets.QApplication(sys.argv)
    win = PhotoViewer()
    win.cap_proc = cap_proc   # ✅ UI에서 Exit 버튼으로 안전하게 종료할 수 있도록 전달
    win.show()
    code = app.exec_()

    # ── 종료 시 색상 정의 저장 (Exit 버튼에서도 호출되지만 안전망)
    save_defs()

    # ── 혹시 프로세스가 남아 있다면 정리
    if cap_proc and cap_proc.poll() is None:
        cap_proc.terminate()
        print("📷 백그라운드 캡쳐 프로세스 종료됨")
