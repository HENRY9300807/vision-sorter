@echo off
chcp 65001 >nul
echo ========================================
echo GitHub 토큰 빠른 설정
echo ========================================
echo.
echo GitHub Personal Access Token (PAT)을 설정합니다.
echo.
echo 1. GitHub 웹사이트에서 토큰 생성:
echo    https://github.com/settings/tokens
echo.
echo 2. "Generate new token" - "Generate new token (classic)" 클릭
echo.
echo 3. 권한 설정:
echo    - repo (전체)
echo    - read:packages
echo.
echo 4. 생성된 토큰을 복사하세요 (ghp_로 시작)
echo.
echo ========================================
set /p TOKEN="토큰을 입력하세요: "
if "%TOKEN%"=="" (
    echo 오류: 토큰이 입력되지 않았습니다.
    pause
    exit /b 1
)
setx GITHUB_TOKEN "%TOKEN%"
echo.
echo [성공] GITHUB_TOKEN 환경변수가 설정되었습니다.
echo.
echo 참고: 새 터미널/프로세스에서만 적용됩니다.
echo       현재 세션에서 사용하려면:
echo       set GITHUB_TOKEN=%TOKEN%
echo.
echo 서버를 재시작하세요:
echo   package\github_bridge\run_server.bat
echo.
pause

