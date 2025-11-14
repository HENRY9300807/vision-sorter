# 큰 파일을 Git 히스토리에서 제거하는 스크립트

Write-Host "Removing large files from Git history..." -ForegroundColor Yellow

# .github.zip 파일을 Git 캐시에서 제거
git rm --cached .github.zip -r 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Removed .github.zip from Git cache" -ForegroundColor Green
}

# 모든 zip 파일 제거
git rm --cached *.zip -r 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Removed *.zip files from Git cache" -ForegroundColor Green
}

# 변경사항 커밋
git add .gitignore
git commit -m "chore: remove large zip files and update .gitignore"

Write-Host "`nDone! Now you can push again:" -ForegroundColor Green
Write-Host "  git push -u origin henry/analysis_color" -ForegroundColor Cyan

