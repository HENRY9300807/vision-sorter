@echo off
chcp 65001 >nul
echo GitHub 실시간 동기화 시작...
cd /d "%~dp0\..\.."
if not exist "package\github_bridge\sync_realtime.py" (
    echo 오류: sync_realtime.py 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)
python package\github_bridge\sync_realtime.py %*
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)

