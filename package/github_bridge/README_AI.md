# GitHub 레포지토리를 AI에게 제공하기

ChatGPT나 다른 AI에게 GitHub 레포지토리의 파일과 이슈를 읽게 하는 방법입니다.

## 빠른 사용법

### 1. 특정 파일들 가져오기

```bash
# main.py와 다른 파일들 가져오기
python package\github_bridge\fetch_for_ai.py --files main.py package/capture_96_limit.py

# 파일을 텍스트 파일로 저장
python package\github_bridge\fetch_for_ai.py --files main.py --output repo_info.txt
```

### 2. 이슈만 가져오기

```bash
# 최근 50개 이슈 가져오기
python package\github_bridge\fetch_for_ai.py --no-files --max-issues 50

# 이슈를 파일로 저장
python package\github_bridge\fetch_for_ai.py --no-files --max-issues 100 --output issues.txt
```

### 3. 파일 + 이슈 모두 가져오기

```bash
# 주요 파일들과 이슈 목록
python package\github_bridge\fetch_for_ai.py \
  --files main.py package/capture_96_limit.py package/image_utils.py \
  --max-issues 20 \
  --output full_repo_info.txt
```

### 4. PowerShell 사용

```powershell
.\package\github_bridge\fetch_for_ai.ps1 -Files main.py,package/capture_96_limit.py -MaxIssues 10
```

## ChatGPT/Cursor AI에 제공하는 방법

### 방법 1: 파일 내용 복사

1. 스크립트로 정보 가져오기:
   ```bash
   python package\github_bridge\fetch_for_ai.py --files main.py --max-issues 10 --output repo_info.txt
   ```

2. `repo_info.txt` 파일을 열어서 내용 복사

3. ChatGPT나 Cursor AI에 붙여넣기:
   ```
   아래는 내 GitHub 레포지토리 정보입니다:
   [repo_info.txt 내용 붙여넣기]
   ```

### 방법 2: 직접 출력

```bash
# 터미널에 직접 출력 (복사하기 쉬움)
python package\github_bridge\fetch_for_ai.py --files main.py --max-issues 5
```

출력된 내용을 복사해서 AI에게 제공하세요.

## 예시: vision-sorter 레포지토리 전체 정보

```bash
# 주요 파일들 + 최근 이슈 50개
python package\github_bridge\fetch_for_ai.py \
  --owner HENRY9300807 \
  --repo vision-sorter \
  --files main.py package/capture_96_limit.py package/image_utils.py ui/color_definition.py \
  --max-issues 50 \
  --output vision-sorter-info.txt
```

## 출력 형식

스크립트는 다음 형식으로 출력합니다:

```markdown
# GitHub Repository: owner/repo

## Repository Information
- Name: owner/repo
- Description: ...
- Default Branch: main
- Stars: 0
- Issues: 702

## File Contents

### main.py
```
[파일 내용]
```

## Issues

### Issue #1: 제목
- State: open
- Created: 2024-01-01T00:00:00Z
- Labels: bug, enhancement
- URL: https://github.com/...
- Body Preview: ...
```

## 주의사항

- 서버가 실행 중이어야 합니다 (`http://localhost:8787`)
- GitHub 토큰이 설정되어 있어야 합니다
- 큰 파일은 시간이 걸릴 수 있습니다
- 이슈가 많으면 `--max-issues`로 제한하세요

