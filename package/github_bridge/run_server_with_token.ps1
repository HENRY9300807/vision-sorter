# GitHub Bridge 서버 실행 (환경 변수 포함)
# 사용법: .\package\github_bridge\run_server_with_token.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = $env:GITHUB_TOKEN
)

if (-not $Token) {
    Write-Host "⚠️  GITHUB_TOKEN이 설정되지 않았습니다." -ForegroundColor Yellow
    Write-Host ""
    $Token = Read-Host "토큰을 입력하세요"
}

if ($Token) {
    $env:GITHUB_TOKEN = $Token
    Write-Host "✅ 토큰이 설정되었습니다!" -ForegroundColor Green
    Write-Host ""
    Write-Host "서버를 시작합니다..." -ForegroundColor Cyan
    Write-Host "  주소: http://localhost:8787" -ForegroundColor White
    Write-Host "  Swagger UI: http://localhost:8787/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "서버를 중지하려면 Ctrl+C를 누르세요" -ForegroundColor Gray
    Write-Host ""
    
    # 서버 실행
    python -m uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787
} else {
    Write-Host "토큰이 입력되지 않았습니다." -ForegroundColor Red
}

