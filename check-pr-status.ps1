# PR #704 상태 확인 스크립트

$repo = "HENRY9300807/vision-sorter"
$prNumber = 704

Write-Host "PR #$prNumber 상태 확인 중..." -ForegroundColor Yellow

try {
    $headers = @{
        "Accept" = "application/vnd.github.v3+json"
    }
    
    # Token이 있으면 사용
    if ($env:GITHUB_TOKEN) {
        $headers["Authorization"] = "token $env:GITHUB_TOKEN"
    }
    
    $pr = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/pulls/$prNumber" -Headers $headers
    
    Write-Host ""
    $title = "PR #$prNumber : $($pr.title)"
    Write-Host $title -ForegroundColor Cyan
    $stateColor = if ($pr.state -eq 'closed') { 'Yellow' } else { 'Green' }
    Write-Host "상태: $($pr.state)" -ForegroundColor $stateColor
    
    if ($pr.merged) {
        Write-Host "✅ 머지됨 (Merged)" -ForegroundColor Green
        Write-Host "머지된 시간: $($pr.merged_at)" -ForegroundColor Gray
    } else {
        Write-Host "❌ 머지되지 않고 닫힘 (Closed without merging)" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "From: $($pr.head.ref) → To: $($pr.base.ref)" -ForegroundColor Gray
    Write-Host "생성: $($pr.created_at)" -ForegroundColor Gray
    Write-Host "닫힘: $($pr.closed_at)" -ForegroundColor Gray
}
catch {
    Write-Host "❌ 오류 발생:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "웹에서 직접 확인:" -ForegroundColor Yellow
    Write-Host "  https://github.com/$repo/pull/$prNumber" -ForegroundColor Cyan
}

