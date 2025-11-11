param([string]$Branch = "main")

Write-Host "✅ Git Auto Sync started on branch '$Branch'"
git checkout -B $Branch

# 파일 변경 감시기
$fsw = New-Object IO.FileSystemWatcher (Get-Location), -1
$fsw.IncludeSubdirectories = $true
$fsw.EnableRaisingEvents = $true

Register-ObjectEvent $fsw Changed -Action {
    Start-Sleep -Milliseconds 1000
    git add -A
    $msg = "auto: sync $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    git commit -m $msg 2>$null
    git push -u origin $Branch 2>$null
    Write-Host "📤 [$msg] pushed to $Branch"
} | Out-Null

Write-Host "🟢 Watching for changes... Press Ctrl+C to stop."
while ($true) { Start-Sleep -Seconds 2 }

