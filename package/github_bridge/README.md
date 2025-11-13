# GitHub Bridge Server

FastAPI 기반 GitHub API 브릿지 서버입니다. GitHub API를 간단한 REST 엔드포인트로 제공합니다.

## 권한 설계 (최소 권한)

### GitHub App Repository permissions (Read):
- Metadata (기본)
- Contents
- Issues
- Pull requests
- Commit statuses
- (선택) Reactions

### Fine‑grained PAT Scopes (Read):
- Repository contents (read)
- Metadata (read)
- (선택) Issues/Pull requests/Commit statuses/Code search

## 설치

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# 또는
source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install fastapi uvicorn httpx PyJWT
```

## 인증 설정

### 방법 1: Fine-grained PAT 사용 (권장)

```bash
# Windows
set GITHUB_TOKEN=ghp_xxx

# Linux/Mac
export GITHUB_TOKEN=ghp_xxx
```

### 방법 2: GitHub App 사용

```bash
export GITHUB_APP_ID=12345
export GITHUB_APP_PRIVATE_KEY_PEM="$(cat private-key.pem)"
export GITHUB_INSTALLATION_ID=67890
```

## 실행

```bash
uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787
```

또는 프로젝트 루트에서:

```bash
uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787
```

## 빠른 점검

```bash
# 사용자 로그인 확인
curl "http://localhost:8787/get_user_login"

# 레포지토리 목록 (소유자)
curl "http://localhost:8787/list_repositories_by_affiliation?affiliation=owner"

# 레포지토리 정보
curl "http://localhost:8787/get_repo?owner=ORG&repo=REPO"

# 파일 가져오기
curl "http://localhost:8787/fetch_file?owner=ORG&repo=REPO&path=README.md"

# 헬스체크
curl "http://localhost:8787/healthz"
```

## API 엔드포인트

### Repository
- `GET /check_repo_initialized` - 레포지토리 초기화 상태 확인
- `GET /get_repo` - 레포지토리 정보
- `GET /list_repositories` - 레포지토리 목록
- `GET /list_repositories_by_affiliation` - 소속별 레포지토리 목록

### Commit / Branch
- `GET /fetch_commit` - 커밋 정보
- `GET /get_commit_combined_status` - 커밋 상태
- `GET /search_commits` - 커밋 검색
- `GET /search_branches` - 브랜치 검색

### 파일/코드
- `GET /fetch_file` - 파일 내용
- `GET /fetch_blob` - Blob 원시 내용
- `GET /search` - 코드 검색

### Issues
- `GET /fetch_issue` - 이슈 정보
- `GET /fetch_issue_comments` - 이슈 댓글
- `GET /list_recent_issues` - 최근 이슈 목록
- `GET /search_issues` - 이슈 검색

### Pull Requests
- `GET /fetch_pr` - PR 정보
- `GET /fetch_pr_comments` - PR 댓글
- `GET /fetch_pr_patch` - PR 패치
- `GET /get_pr_diff` - PR diff
- `GET /list_pr_changed_filenames` - 변경된 파일 목록

### 사용자/조직
- `GET /get_profile` - 사용자 프로필
- `GET /get_user_login` - 사용자 로그인 이름
- `GET /list_user_orgs` - 사용자 조직 목록

## Swagger UI

서버 실행 후 브라우저에서 접속:

```
http://localhost:8787/docs
```

## 참고사항

- 모든 엔드포인트는 읽기 전용입니다
- 인증은 PAT 또는 GitHub App을 사용합니다
- 타임아웃은 30초로 설정되어 있습니다

