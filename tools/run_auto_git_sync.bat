@echo off
REM Git 자동 동기화 스크립트 실행 (Windows)
cd /d "%~dp0\.."
python tools/auto_git_sync.py
pause

