@echo off
REM GitHub Bridge 서버 실행 스크립트 (Windows)
cd /d "%~dp0\..\.."
python -m uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787

