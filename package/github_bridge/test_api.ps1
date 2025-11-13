# GitHub Bridge API 테스트 스크립트
# 사용법: .\package\github_bridge\test_api.ps1

$baseUrl = "http://localhost:8787"

Write-Host "=== GitHub Bridge API 테스트 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 헬스체크
Write-Host "1. 헬스체크 테스트..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/healthz" -Method Get
    Write-Host "✅ 헬스체크 성공: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "❌ 헬스체크 실패: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. 인증 확인
if (-not $env:GITHUB_TOKEN) {
    Write-Host "⚠️  GITHUB_TOKEN이 설정되지 않았습니다." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "GitHub API를 사용하려면 토큰이 필요합니다:" -ForegroundColor Cyan
    Write-Host "  방법 1: PAT (Personal Access Token)" -ForegroundColor White
    Write-Host "    `$env:GITHUB_TOKEN = 'ghp_xxx'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  방법 2: GitHub App" -ForegroundColor White
    Write-Host "    `$env:GITHUB_APP_ID = '12345'" -ForegroundColor Gray
    Write-Host "    `$env:GITHUB_APP_PRIVATE_KEY_PEM = '-----BEGIN RSA PRIVATE KEY-----...'" -ForegroundColor Gray
    Write-Host "    `$env:GITHUB_INSTALLATION_ID = '67890'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "토큰 생성 방법:" -ForegroundColor Cyan
    Write-Host "  1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens" -ForegroundColor White
    Write-Host "  2. 'Generate new token' 클릭" -ForegroundColor White
    Write-Host "  3. Repository permissions: Contents (Read), Metadata (Read) 선택" -ForegroundColor White
    Write-Host "  4. 토큰 생성 후 위 명령어로 설정" -ForegroundColor White
    Write-Host ""
    exit 0
}

Write-Host "2. 사용자 로그인 확인..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/get_user_login" -Method Get
    Write-Host "✅ 로그인 사용자: $($response.login)" -ForegroundColor Green
} catch {
    Write-Host "❌ 인증 실패: $_" -ForegroundColor Red
    Write-Host "   토큰이 유효한지 확인하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 3. 레포지토리 정보
Write-Host "3. 레포지토리 정보 가져오기..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/get_repo?owner=HENRY9300807&repo=vision-sorter" -Method Get
    Write-Host "✅ 레포지토리: $($response.full_name)" -ForegroundColor Green
    Write-Host "   설명: $($response.description)" -ForegroundColor Gray
    Write-Host "   기본 브랜치: $($response.default_branch)" -ForegroundColor Gray
    Write-Host "   Stars: $($response.stargazers_count)" -ForegroundColor Gray
    Write-Host "   Issues: $($response.open_issues_count)" -ForegroundColor Gray
} catch {
    Write-Host "❌ 레포지토리 정보 가져오기 실패: $_" -ForegroundColor Red
}

Write-Host ""

# 4. 레포지토리 목록
Write-Host "4. 레포지토리 목록 (소유자)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/list_repositories_by_affiliation?affiliation=owner&per_page=5" -Method Get
    Write-Host "✅ 레포지토리 개수: $($response.Count)" -ForegroundColor Green
    foreach ($repo in $response[0..4]) {
        Write-Host "   - $($repo.full_name)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ 레포지토리 목록 가져오기 실패: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 테스트 완료 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Swagger UI에서 더 많은 API를 테스트할 수 있습니다:" -ForegroundColor Cyan
Write-Host "  http://localhost:8787/docs" -ForegroundColor White

