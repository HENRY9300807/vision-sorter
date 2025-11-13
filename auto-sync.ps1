param([int]$DebounceMs = 1500)

Set-Location "$PSScriptRoot"

# 변경 감지기
$fsw = New-Object IO.FileSystemWatcher -Property @{
  Path = (Get-Location).Path
  Filter = '*.*'
  IncludeSubdirectories = $true
  EnableRaisingEvents = $true
}

$changed = $false
$act = {
  $global:changed = $true
}
Register-ObjectEvent $fsw Changed -SourceIdentifier FSW_Changed -Action $act | Out-Null
Register-ObjectEvent $fsw Created -SourceIdentifier FSW_Created -Action $act | Out-Null
Register-ObjectEvent $fsw Deleted -SourceIdentifier FSW_Deleted -Action $act | Out-Null
Register-ObjectEvent $fsw Renamed -SourceIdentifier FSW_Renamed -Action $act | Out-Null

Write-Host "Auto-sync started. Watching $(Get-Location). Press Ctrl+C to stop."

while ($true) {
  if ($changed) {
    Start-Sleep -Milliseconds $DebounceMs
    $changed = $false
    # 변경 없으면 스킵
    $status = git status --porcelain
    if (-not $status) { continue }

    git add -A
    $msg = "autosync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    git commit -m $msg
    git push
    Write-Host "[PUSHED] $msg"
  }
  Start-Sleep -Milliseconds 250
}

