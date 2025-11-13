# GitHub 토큰 설정 가이드
# 사용법: .\package\github_bridge\setup_token.ps1

Write-Host "=== GitHub 토큰 설정 가이드 ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. GitHub에서 토큰 생성:" -ForegroundColor Yellow
Write-Host "   - https://github.com/settings/tokens 접속" -ForegroundColor White
Write-Host "   - 'Fine-grained tokens' → 'Generate new token' 클릭" -ForegroundColor White
Write-Host "   - 토큰 이름 입력 (예: 'GitHub Bridge')" -ForegroundColor White
Write-Host "   - 만료 기간 설정" -ForegroundColor White
Write-Host "   - Repository access: 'Selected repositories' → 'vision-sorter' 선택" -ForegroundColor White
Write-Host "   - Repository permissions:" -ForegroundColor White
Write-Host "     * Contents: Read" -ForegroundColor Gray
Write-Host "     * Metadata: Read" -ForegroundColor Gray
Write-Host "     * Issues: Read (선택)" -ForegroundColor Gray
Write-Host "     * Pull requests: Read (선택)" -ForegroundColor Gray
Write-Host "   - 'Generate token' 클릭 후 토큰 복사" -ForegroundColor White
Write-Host ""

Write-Host "2. 토큰 설정 (PowerShell):" -ForegroundColor Yellow
Write-Host "   `$env:GITHUB_TOKEN = 'ghp_여기에_토큰_붙여넣기'" -ForegroundColor Green
Write-Host ""

Write-Host "3. 영구 설정 (선택):" -ForegroundColor Yellow
Write-Host "   [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_xxx', 'User')" -ForegroundColor Green
Write-Host ""

Write-Host "4. 테스트:" -ForegroundColor Yellow
Write-Host "   .\package\github_bridge\test_api.ps1" -ForegroundColor Green
Write-Host ""

Write-Host "⚠️  보안 주의:" -ForegroundColor Red
Write-Host "   - 토큰을 절대 공개 저장소에 커밋하지 마세요!" -ForegroundColor Yellow
Write-Host "   - .gitignore에 .env 파일 추가 권장" -ForegroundColor Yellow
Write-Host ""

