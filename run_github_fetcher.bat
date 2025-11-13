@echo off
chcp 65001 >nul
echo ========================================
echo GitHub Repository Fetcher GUI
echo ========================================
echo.

cd /d "%~dp0"

if not exist "package\github_bridge\gui_fetch.py" (
    echo [오류] gui_fetch.py 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo GUI 프로그램을 시작합니다...
echo.

python package\github_bridge\gui_fetch.py

if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 오류가 발생했습니다.
    echo.
    echo 확인사항:
    echo 1. Python이 설치되어 있는지 확인
    echo 2. PyQt5가 설치되어 있는지 확인 (pip install PyQt5)
    echo 3. GitHub Bridge 서버가 실행 중인지 확인 (http://localhost:8787)
    echo.
    pause
)

