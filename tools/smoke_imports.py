# -*- coding: utf-8 -*-
"""
CI 헤드리스 환경에서 '필수 모듈이 최소한 임포트는 되는지'만 확인.
GUI/카메라 동작은 CI에서 수행하지 않음.
"""
import importlib
import sys
import os

# CI 환경에서는 Qt를 오프스크린으로 설정
if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

mods = [
    "PyQt5.QtWidgets",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "cv2",
    "numpy",
    "matplotlib",
]

# 선택적 모듈 (하드웨어 의존성 - CI에서 없어도 OK)
optional_mods = [
    "pypylon",
]

ok = True
for m in mods:
    try:
        importlib.import_module(m)
        print(f"[OK] import {m}")
    except Exception as e:
        ok = False
        print(f"[FAIL] import {m}: {e}", file=sys.stderr)

# 선택적 모듈은 경고만
for m in optional_mods:
    try:
        importlib.import_module(m)
        print(f"[OK] import {m} (optional)")
    except Exception as e:
        print(f"[SKIP] import {m} (optional, not available in CI): {e}")

sys.exit(0 if ok else 1)

