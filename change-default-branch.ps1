# GitHub 기본 브랜치 변경 스크립트
# 사용법: .\change-default-branch.ps1 -Token "your_github_token"

param(
    [string]$Token = $env:GITHUB_TOKEN,
    [string]$Repo = "HENRY9300807/vision-sorter",
    [string]$NewDefaultBranch = "henry/analysis_color"
)

if (-not $Token) {
    Write-Host "GitHub Personal Access Token이 필요합니다." -ForegroundColor Red
    Write-Host "방법 1: 환경변수 설정" -ForegroundColor Yellow
    Write-Host "  `$env:GITHUB_TOKEN = 'your_token_here'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "방법 2: 스크립트에 직접 전달" -ForegroundColor Yellow
    Write-Host "  .\change-default-branch.ps1 -Token 'your_token_here'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "방법 3: GitHub 웹사이트에서 수동 변경 (추천)" -ForegroundColor Yellow
    Write-Host "  https://github.com/$Repo/settings/branches" -ForegroundColor Cyan
    exit 1
}

Write-Host "기본 브랜치를 '$NewDefaultBranch'로 변경 중..." -ForegroundColor Yellow

$headers = @{
    "Authorization" = "token $Token"
    "Accept" = "application/vnd.github.v3+json"
}

$body = @{
    default_branch = $NewDefaultBranch
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo" -Method PATCH -Headers $headers -Body $body
    
    Write-Host "✅ 기본 브랜치가 '$NewDefaultBranch'로 변경되었습니다!" -ForegroundColor Green
    Write-Host "이제 main 브랜치를 삭제할 수 있습니다:" -ForegroundColor Cyan
    Write-Host "  git push origin --delete main" -ForegroundColor Yellow
}
catch {
    Write-Host "❌ 오류 발생:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "수동으로 변경하는 방법:" -ForegroundColor Yellow
    Write-Host "  https://github.com/$Repo/settings/branches" -ForegroundColor Cyan
}

