# GitHub 토큰 빠른 설정 스크립트
# 사용법: .\package\github_bridge\quick_setup.ps1

Write-Host "=== GitHub 토큰 빠른 설정 ===" -ForegroundColor Cyan
Write-Host ""

# 현재 토큰 확인
if ($env:GITHUB_TOKEN) {
    Write-Host "현재 설정된 토큰: $($env:GITHUB_TOKEN.Substring(0, [Math]::Min(10, $env:GITHUB_TOKEN.Length)))..." -ForegroundColor Yellow
    $useExisting = Read-Host "기존 토큰을 사용하시겠습니까? (Y/N)"
    if ($useExisting -eq "Y" -or $useExisting -eq "y") {
        Write-Host "기존 토큰 사용" -ForegroundColor Green
        .\package\github_bridge\test_api.ps1
        exit 0
    }
}

Write-Host ""
Write-Host "GitHub 토큰 생성 방법:" -ForegroundColor Yellow
Write-Host "1. 브라우저에서 다음 주소 열기:" -ForegroundColor White
Write-Host "   https://github.com/settings/tokens?type=beta" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. 'Generate new token' 클릭" -ForegroundColor White
Write-Host ""
Write-Host "3. 설정:" -ForegroundColor White
Write-Host "   - Token name: GitHub Bridge" -ForegroundColor Gray
Write-Host "   - Expiration: 원하는 기간 선택" -ForegroundColor Gray
Write-Host "   - Repository access: Selected repositories" -ForegroundColor Gray
Write-Host "   - vision-sorter 선택" -ForegroundColor Gray
Write-Host "   - Repository permissions:" -ForegroundColor Gray
Write-Host "     * Contents: Read" -ForegroundColor Gray
Write-Host "     * Metadata: Read" -ForegroundColor Gray
Write-Host "     * Issues: Read (선택)" -ForegroundColor Gray
Write-Host "     * Pull requests: Read (선택)" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 'Generate token' 클릭 후 토큰 복사" -ForegroundColor White
Write-Host ""

$token = Read-Host "생성한 토큰을 붙여넣으세요 (ghp_로 시작)"

if (-not $token) {
    Write-Host "토큰이 입력되지 않았습니다." -ForegroundColor Red
    exit 1
}

if (-not $token.StartsWith("ghp_")) {
    Write-Host "⚠️  경고: 토큰은 보통 'ghp_'로 시작합니다. 올바른 토큰인지 확인하세요." -ForegroundColor Yellow
    $continue = Read-Host "계속하시겠습니까? (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        exit 0
    }
}

# 토큰 설정
$env:GITHUB_TOKEN = $token
Write-Host ""
Write-Host "✅ 토큰이 설정되었습니다!" -ForegroundColor Green
Write-Host ""

# 영구 설정 여부 확인
$savePermanent = Read-Host "시스템 환경 변수에 영구 저장하시겠습니까? (Y/N)"
if ($savePermanent -eq "Y" -or $savePermanent -eq "y") {
    [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', $token, 'User')
    Write-Host "✅ 환경 변수에 영구 저장되었습니다." -ForegroundColor Green
    Write-Host "   (새 PowerShell 창에서도 사용 가능)" -ForegroundColor Gray
} else {
    Write-Host "⚠️  현재 세션에만 저장되었습니다." -ForegroundColor Yellow
    Write-Host "   (PowerShell 창을 닫으면 사라집니다)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== API 테스트 시작 ===" -ForegroundColor Cyan
Write-Host ""

# API 테스트 실행
.\package\github_bridge\test_api.ps1

