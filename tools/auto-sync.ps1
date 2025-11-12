param(
  [string]$Branch = "main",
  [int]$IntervalSec = 3
)

$ErrorActionPreference = "SilentlyContinue"

# 레포 루트 = (tools\auto-sync.ps1)의 상위 폴더
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

Write-Host "✅ Git Auto Sync (polling) started at $repoRoot on branch '$Branch'"
git checkout -B $Branch | Out-Null

function Sync-Once {
    $changes = git status --porcelain
    if (-not $changes) { return }

    Write-Host "📝 Changes detected:`n$changes"
    git add -A

    $msg = "auto: sync $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    git commit -m $msg | Out-Null

    # 원격 최신 반영 후 푸시(충돌 방지)
    git fetch origin $Branch | Out-Null
    git pull --rebase origin $Branch | Out-Null

    git push -u origin $Branch
    Write-Host "📤 $msg"
}

while ($tue) {
    Sync-Once
    Start-Sleep -Seconds $IntervalSec
}
