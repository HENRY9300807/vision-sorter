# 브랜치의 모든 파일을 GPT용으로 가져오는 스크립트

param(
    [string]$Owner = "HENRY9300807",
    [string]$Repo = "vision-sorter",
    [int]$MaxIssues = 0,
    [string]$Output = "all_files_for_gpt.txt"
)

Write-Host "=== 브랜치의 모든 파일 가져오기 ===" -ForegroundColor Cyan
Write-Host "레포지토리: $Owner/$Repo" -ForegroundColor White
Write-Host ""

$noIssuesArg = if ($MaxIssues -eq 0) { "--no-issues" } else { "--max-issues $MaxIssues" }

$cmd = "python package\github_bridge\fetch_for_ai.py --owner $Owner --repo $Repo --all-files $noIssuesArg --output $Output"

Write-Host "실행 중..." -ForegroundColor Yellow
Invoke-Expression $cmd

if (Test-Path $Output) {
    Write-Host ""
    Write-Host "✅ 완료! $Output 파일이 생성되었습니다." -ForegroundColor Green
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Cyan
    Write-Host "1. 파일 열기: notepad $Output" -ForegroundColor Yellow
    Write-Host "2. 전체 내용 선택 (Ctrl+A)" -ForegroundColor Yellow
    Write-Host "3. 복사 (Ctrl+C)" -ForegroundColor Yellow
    Write-Host "4. GPT 채팅창에 붙여넣기 (Ctrl+V)" -ForegroundColor Yellow
    Write-Host ""
    
    $fileInfo = Get-Item $Output
    $fileSizeKB = [math]::Round($fileInfo.Length / 1KB, 2)
    Write-Host "파일 크기: $fileSizeKB KB" -ForegroundColor Gray
    
    # GPT 토큰 제한 안내 (대략적으로)
    if ($fileSizeKB -gt 500) {
        Write-Host ""
        Write-Host "⚠️  파일이 큽니다. GPT는 한 번에 제한된 양만 처리할 수 있습니다." -ForegroundColor Yellow
        Write-Host "   필요시 파일을 여러 부분으로 나눠서 제공하세요." -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ 오류: 파일이 생성되지 않았습니다." -ForegroundColor Red
}

