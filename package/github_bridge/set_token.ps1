# GitHub 토큰 간단 설정 스크립트
# 사용법: .\package\github_bridge\set_token.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$Token
)

if (-not $Token) {
    Write-Host "=== GitHub 토큰 설정 ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "GitHub에서 토큰을 생성하세요:" -ForegroundColor Yellow
    Write-Host "  https://github.com/settings/tokens?type=beta" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "토큰 생성 후 아래 명령어로 설정:" -ForegroundColor Yellow
    Write-Host "  .\package\github_bridge\set_token.ps1 -Token 'ghp_여기에_토큰'" -ForegroundColor Green
    Write-Host ""
    Write-Host "또는 직접 입력:" -ForegroundColor Yellow
    $Token = Read-Host "토큰을 입력하세요"
}

if ($Token) {
    $env:GITHUB_TOKEN = $Token
    Write-Host ""
    Write-Host "✅ 토큰이 설정되었습니다!" -ForegroundColor Green
    Write-Host ""
    
    # 테스트 실행
    Write-Host "API 테스트 중..." -ForegroundColor Yellow
    .\package\github_bridge\test_api.ps1
} else {
    Write-Host "토큰이 입력되지 않았습니다." -ForegroundColor Red
}

