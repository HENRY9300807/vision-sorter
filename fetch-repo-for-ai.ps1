# GitHub 레포지토리 정보를 AI용으로 가져오는 간편 스크립트
# 사용법: .\fetch-repo-for-ai.ps1 [파일경로들]

param(
    [string]$Owner = "HENRY9300807",
    [string]$Repo = "vision-sorter",
    [string[]]$Files = @(),
    [switch]$AllFiles,
    [int]$MaxIssues = 10,
    [switch]$NoIssues,
    [string]$Output = ""
)

Write-Host "=== GitHub 레포지토리 정보 가져오기 ===" -ForegroundColor Cyan
Write-Host "레포지토리: $Owner/$Repo" -ForegroundColor White
Write-Host ""

# 파일 목록 결정
if ($AllFiles) {
    Write-Host "모든 파일을 가져옵니다..." -ForegroundColor Yellow
    $filesArg = "--all-files"
} elseif ($Files.Count -eq 0) {
    Write-Host "파일을 자동으로 탐색합니다..." -ForegroundColor Yellow
    $filesArg = "--auto-files"
} else {
    $filesList = $Files -join " "
    $filesArg = "--files $filesList"
}

$noIssuesArg = ""
if ($NoIssues) {
    $noIssuesArg = "--no-issues"
}

$outputArg = ""
if ($Output) {
    $outputArg = "--output $Output"
    Write-Host "결과를 파일로 저장: $Output" -ForegroundColor Yellow
}

$cmd = "python package\github_bridge\fetch_for_ai.py --owner $Owner --repo $Repo $filesArg --max-issues $MaxIssues $noIssuesArg $outputArg"

Write-Host ""
Invoke-Expression $cmd

if ($Output) {
    Write-Host ""
    Write-Host "✅ 결과가 $Output 파일에 저장되었습니다." -ForegroundColor Green
    Write-Host "   이 파일의 내용을 복사해서 GPT에 붙여넣으세요." -ForegroundColor Cyan
}

