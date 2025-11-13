@echo off
chcp 65001 >nul
echo GitHub Repository Fetcher GUI 실행 중...
cd /d "%~dp0\..\.."
if not exist "package\github_bridge\gui_fetch.py" (
    echo 오류: gui_fetch.py 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)
python package\github_bridge\gui_fetch.py
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)

