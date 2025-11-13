@echo off
chcp 65001 >nul
echo ========================================
echo GitHub Bridge 서버 재시작 및 토큰 설정
echo ========================================
echo.

REM 기존 서버 프로세스 종료
echo [1/4] 기존 서버 프로세스 확인 중...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787 ^| findstr LISTENING') do (
    echo 서버 프로세스 종료 중 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 >nul
)

echo.
echo [2/4] GitHub 토큰 확인 중...
if "%GITHUB_TOKEN%"=="" (
    echo [경고] GITHUB_TOKEN이 설정되지 않았습니다.
    echo.
    echo 토큰 설정 방법:
    echo   1. https://github.com/settings/tokens/new 접속
    echo   2. "Generate new token (classic)" 클릭
    echo   3. repo 권한 체크
    echo   4. 토큰 생성 후 복사
    echo.
    set /p TOKEN="토큰을 입력하세요 (또는 Enter로 건너뛰기): "
    if not "!TOKEN!"=="" (
        set GITHUB_TOKEN=!TOKEN!
        echo [OK] 토큰이 현재 세션에 설정되었습니다.
    ) else (
        echo [경고] 토큰 없이 서버를 시작합니다. (API 호출 시 오류 발생)
    )
) else (
    echo [OK] GITHUB_TOKEN이 설정되어 있습니다.
)

echo.
echo [3/4] 서버 시작 중...
cd /d "%~dp0\..\.."
start "GitHub Bridge Server" cmd /c "python -m uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787"
timeout /t 3 >nul

echo.
echo [4/4] 서버 상태 확인 중...
timeout /t 2 >nul
curl -s http://localhost:8787/healthz >nul 2>&1
if errorlevel 1 (
    echo [경고] 서버가 아직 시작되지 않았을 수 있습니다.
    echo        잠시 후 다시 시도하세요.
) else (
    echo [성공] 서버가 정상적으로 시작되었습니다!
)

echo.
echo ========================================
echo 완료!
echo ========================================
echo.
echo 서버 주소: http://localhost:8787
echo.
if "%GITHUB_TOKEN%"=="" (
    echo [중요] 토큰을 설정하지 않았습니다.
    echo       PowerShell에서 다음 명령을 실행하세요:
    echo       $env:GITHUB_TOKEN = 'ghp_여기에_토큰'
    echo       그 후 서버를 재시작하세요.
)
echo.
pause

