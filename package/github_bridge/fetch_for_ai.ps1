# GitHub 레포지토리 정보를 AI용으로 가져오기 (PowerShell 래퍼)
# 사용법: .\package\github_bridge\fetch_for_ai.ps1

param(
    [string]$Owner = "HENRY9300807",
    [string]$Repo = "vision-sorter",
    [string[]]$Files = @(),
    [switch]$NoIssues,
    [int]$MaxIssues = 50,
    [string]$Output = ""
)

$filesArg = ""
if ($Files.Count -gt 0) {
    $filesArg = "--files " + ($Files -join " ")
}

$noIssuesArg = ""
if ($NoIssues) {
    $noIssuesArg = "--no-issues"
}

$outputArg = ""
if ($Output) {
    $outputArg = "--output $Output"
}

$cmd = "python package\github_bridge\fetch_for_ai.py --owner $Owner --repo $Repo $filesArg $noIssuesArg --max-issues $MaxIssues $outputArg"

Write-Host "=== GitHub 레포지토리 정보 가져오기 ===" -ForegroundColor Cyan
Write-Host "레포지토리: $Owner/$Repo" -ForegroundColor White
Write-Host ""

Invoke-Expression $cmd

