# GitHub Bridge 패키지 파일 검증 스크립트

Write-Host "GitHub Bridge 파일 검증 시작..." -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# 프로젝트 루트 확인
$projectRoot = Get-Location
$githubBridgeDir = Join-Path $projectRoot "package\github_bridge"

if (-not (Test-Path $githubBridgeDir)) {
    Write-Host "❌ package\github_bridge 폴더를 찾을 수 없습니다!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 프로젝트 루트: $projectRoot" -ForegroundColor Green
Write-Host "✅ GitHub Bridge 디렉토리: $githubBridgeDir" -ForegroundColor Green
Write-Host ""

# 주요 파일 확인
$requiredFiles = @(
    "main.py",
    "sync_realtime.py",
    "gui_fetch.py",
    "fetch_for_ai.py",
    "check_server.py"
)

$requiredBatches = @(
    "run_sync.bat",
    "run_server.bat",
    "run_gui.bat"
)

$requiredDocs = @(
    "README.md",
    "GUI_사용법.md",
    "실시간동기화_사용법.md"
)

Write-Host "📄 필수 Python 파일 확인..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    $filePath = Join-Path $githubBridgeDir $file
    if (Test-Path $filePath) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file (없음)" -ForegroundColor Red
        $errors += "필수 파일 없음: $file"
    }
}

Write-Host ""
Write-Host "📄 필수 Batch 파일 확인..." -ForegroundColor Yellow
foreach ($file in $requiredBatches) {
    $filePath = Join-Path $githubBridgeDir $file
    if (Test-Path $filePath) {
        Write-Host "  ✅ $file" -ForegroundColor Green
        
        # Batch 파일 내용 확인
        $content = Get-Content $filePath -Raw
        if ($content -match "OneDrive") {
            Write-Host "    ⚠️  OneDrive 경로가 포함되어 있습니다!" -ForegroundColor Yellow
            $warnings += "${file}: OneDrive 경로 포함"
        }
    } else {
        Write-Host "  ❌ $file (없음)" -ForegroundColor Red
        $errors += "필수 파일 없음: $file"
    }
}

Write-Host ""
Write-Host "📄 문서 파일 확인..." -ForegroundColor Yellow
foreach ($file in $requiredDocs) {
    $filePath = Join-Path $githubBridgeDir $file
    if (Test-Path $filePath) {
        Write-Host "  ✅ $file" -ForegroundColor Green
        
        # OneDrive 경로 확인
        $content = Get-Content $filePath -Raw
        if ($content -match "OneDrive|C:\\Users\\kn666\\OneDrive") {
            Write-Host "    ⚠️  OneDrive 경로가 포함되어 있습니다!" -ForegroundColor Yellow
            $warnings += "${file}: OneDrive 경로 포함"
        }
        
        # 올바른 경로 확인
        if ($content -match '\$env:USERPROFILE\\Desktop\\analysis_color') {
            Write-Host "    ✅ 올바른 경로 형식 사용" -ForegroundColor Green
        }
    } else {
        Write-Host "  ⚠️  $file (없음)" -ForegroundColor Yellow
        $warnings += "문서 파일 없음: $file"
    }
}

Write-Host ""
Write-Host "🔍 추가 검사..." -ForegroundColor Yellow

# 루트의 auto-sync.ps1 확인
$autoSync = Join-Path $projectRoot "auto-sync.ps1"
if (Test-Path $autoSync) {
    Write-Host "  ✅ auto-sync.ps1 (루트)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  auto-sync.ps1 없음 (필요시 생성)" -ForegroundColor Yellow
}

# .gitignore 확인
$gitignore = Join-Path $projectRoot ".gitignore"
if (Test-Path $gitignore) {
    Write-Host "  ✅ .gitignore" -ForegroundColor Green
    $ignoreContent = Get-Content $gitignore -Raw
    if ($ignoreContent -match "\.zip" -or $ignoreContent -match "\.github\.zip") {
        Write-Host "    ✅ zip 파일 무시 설정됨" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️  .gitignore 없음" -ForegroundColor Yellow
    $warnings += ".gitignore 파일 없음"
}

Write-Host ""
Write-Host ("=" * 50)
Write-Host ""

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✅ 모든 파일이 정상입니다!" -ForegroundColor Green
    exit 0
} elseif ($errors.Count -eq 0) {
    Write-Host "⚠️  경고사항이 있습니다:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host ("  - " + $warning) -ForegroundColor Yellow
    }
    exit 0
} else {
        Write-Host "❌ 오류가 발견되었습니다:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host ("  - " + $error) -ForegroundColor Red
    }
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  경고사항:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host ("  - " + $warning) -ForegroundColor Yellow
        }
    }
    exit 1
}

