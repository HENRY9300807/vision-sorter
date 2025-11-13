# github_bridge/main.py
# pyright: reportMissingImports=none
from __future__ import annotations

import os, time, base64, json
from typing import Optional, List, Dict, Any
import httpx  # type: ignore
from fastapi import FastAPI, HTTPException, Query  # type: ignore
from fastapi.responses import PlainTextResponse, StreamingResponse  # type: ignore
import jwt  # type: ignore # PyJWT

GITHUB_API = "https://api.github.com"
ACCEPT_JSON = {"Accept": "application/vnd.github+json"}

app = FastAPI(title="GitHub Bridge", version="0.1.0")

# ---------------------------
# Auth: App or PAT
# ---------------------------
def _bearer_headers() -> Dict[str, str]:
    """Choose PAT or App Installation token."""
    pat = os.getenv("GITHUB_TOKEN")  # Fine-grained PAT
    if pat:
        return {"Authorization": f"Bearer {pat}", **ACCEPT_JSON}

    app_id = os.getenv("GITHUB_APP_ID")
    app_key = os.getenv("GITHUB_APP_PRIVATE_KEY_PEM")
    inst_id = os.getenv("GITHUB_INSTALLATION_ID")
    if not (app_id and app_key and inst_id):
        raise HTTPException(
            status_code=500,
            detail="GitHub 인증 토큰이 설정되지 않았습니다. GITHUB_TOKEN 환경변수를 설정하거나 GitHub App 설정을 완료하세요. 자세한 내용은 package/github_bridge/README.md를 참조하세요."
        )

    # 1) App JWT
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 540, "iss": app_id}
    app_jwt = jwt.encode(payload, app_key, algorithm="RS256")  # type: ignore

    # 2) Installation Access Token
    headers = {"Authorization": f"Bearer {app_jwt}", **ACCEPT_JSON}
    url = f"{GITHUB_API}/app/installations/{inst_id}/access_tokens"
    with httpx.Client(timeout=30.0) as s:
        r = s.post(url, headers=headers)
    if r.status_code >= 300:
        raise RuntimeError(f"Create installation token failed: {r.status_code} {r.text}")
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}", **ACCEPT_JSON}


def _gh_get(path: str, params: Dict[str, Any] | None = None, accept: Optional[str] = None) -> httpx.Response:
    headers = _bearer_headers()
    if accept:
        headers["Accept"] = accept
    with httpx.Client(timeout=30.0) as s:
        r = s.get(f"{GITHUB_API}{path}", headers=headers, params=params)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Not found: {path}")
    if r.status_code >= 300:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r


# ---------------------------
# 1) Repository 상태/메타
# ---------------------------
@app.get("/check_repo_initialized")
def check_repo_initialized(owner: str, repo: str) -> Dict[str, Any]:
    # get_repo + README 존재 여부 + default_branch 확인
    meta = _gh_get(f"/repos/{owner}/{repo}").json()
    default_branch = meta.get("default_branch")
    has_readme = False
    try:
        _ = _gh_get(f"/repos/{owner}/{repo}/contents/README.md", params={"ref": default_branch}).json()
        has_readme = True
    except HTTPException:
        # try uppercase/lowercase variants
        try:
            _ = _gh_get(f"/repos/{owner}/{repo}/contents/README.MD", params={"ref": default_branch})
            has_readme = True
        except HTTPException:
            pass
    return {
        "exists": True,
        "full_name": meta.get("full_name"),
        "private": meta.get("private"),
        "default_branch": default_branch,
        "has_readme": has_readme,
    }


@app.get("/get_repo")
def get_repo(owner: str, repo: str) -> Dict[str, Any]:
    return _gh_get(f"/repos/{owner}/{repo}").json()


@app.get("/get_repo_collaborator_permission")
def get_repo_collaborator_permission(owner: str, repo: str, username: str):
    r = _gh_get(f"/repos/{owner}/{repo}/collaborators/{username}/permission")
    return r.json()


@app.get("/list_repositories")
def list_repositories(per_page: int = 100, page: int = 1):
    r = _gh_get("/user/repos", params={"per_page": per_page, "page": page})
    return r.json()


@app.get("/list_repositories_by_affiliation")
def list_repositories_by_affiliation(affiliation: str = "owner,collaborator,organization_member",
                                     per_page: int = 100, page: int = 1):
    r = _gh_get("/user/repos", params={"affiliation": affiliation, "per_page": per_page, "page": page})
    return r.json()


@app.get("/list_repositories_by_installation")
def list_repositories_by_installation(per_page: int = 100, page: int = 1):
    # App Installation token required
    r = _gh_get("/installation/repositories", params={"per_page": per_page, "page": page})
    return r.json()


# ---------------------------
# 2) Commit / Branch
# ---------------------------
@app.get("/fetch_commit")
def fetch_commit(owner: str, repo: str, sha: str):
    return _gh_get(f"/repos/{owner}/{repo}/commits/{sha}").json()


@app.get("/get_commit_combined_status")
def get_commit_combined_status(owner: str, repo: str, ref: str):
    return _gh_get(f"/repos/{owner}/{repo}/commits/{ref}/status").json()


@app.get("/search_commits")
def search_commits(q: str, per_page: int = 30, page: int = 1):
    # Include repo:owner/name in q if you want to scope it
    return _gh_get("/search/commits", params={"q": q, "per_page": per_page, "page": page}).json()


@app.get("/search_branches")
def search_branches(owner: str, repo: str, q: str = "", per_page: int = 100, page: int = 1):
    # GitHub에 'search branches' 정식 엔드포인트는 없으므로 목록 후 필터
    branches = _gh_get(f"/repos/{owner}/{repo}/branches", params={"per_page": per_page, "page": page}).json()
    if q:
        branches = [b for b in branches if q.lower() in b.get("name","").lower()]
    return branches


# ---------------------------
# 3) 파일/코드
# ---------------------------
@app.get("/fetch_file")
def fetch_file(owner: str, repo: str, path: str, ref: Optional[str] = None):
    r = _gh_get(f"/repos/{owner}/{repo}/contents/{path}", params={"ref": ref} if ref else None)
    j = r.json()
    if isinstance(j, list):
        # directory listing
        return {"type": "dir", "entries": j}
    if j.get("type") == "file":
        content_b64 = j.get("content", "")
        try:
            content = base64.b64decode(content_b64.encode()).decode("utf-8", "replace")
        except Exception:
            content = base64.b64decode(content_b64.encode())
        return {"type": "file", "encoding": "base64", "decoded": content, "raw": content_b64, "sha": j.get("sha")}
    return j


@app.get("/fetch_blob", response_class=PlainTextResponse)
def fetch_blob(owner: str, repo: str, sha: str):
    # Return raw decoded content
    j = _gh_get(f"/repos/{owner}/{repo}/git/blobs/{sha}").json()
    if j.get("encoding") == "base64":
        return base64.b64decode(j["content"]).decode("utf-8", "replace")
    return j.get("content","")


@app.get("/search")
def search_code(q: str, per_page: int = 30, page: int = 1):
    # q 예: "path:ui filename:main.py repo:ORG/REPO term"
    return _gh_get("/search/code", params={"q": q, "per_page": per_page, "page": page}).json()


@app.get("/fetch")
def fetch(url: str, accept_raw: bool = False):
    # raw.githubusercontent.com 등 직접 URL 지원
    headers = {}
    if accept_raw:
        headers["Accept"] = "application/vnd.github.raw"
    with httpx.Client(timeout=30.0) as s:
        r = s.get(url, headers=headers)
    if r.status_code >= 300:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return PlainTextResponse(r.text)


# ---------------------------
# 4) Issues
# ---------------------------
@app.get("/fetch_issue")
def fetch_issue(owner: str, repo: str, number: int):
    return _gh_get(f"/repos/{owner}/{repo}/issues/{number}").json()


@app.get("/fetch_issue_comments")
def fetch_issue_comments(owner: str, repo: str, number: int, per_page: int = 100, page: int = 1):
    return _gh_get(f"/repos/{owner}/{repo}/issues/{number}/comments",
                   params={"per_page": per_page, "page": page}).json()


@app.get("/get_issue_comment_reactions")
def get_issue_comment_reactions(owner: str, repo: str, comment_id: int, per_page: int = 100, page: int = 1):
    # Reactions API
    return _gh_get(f"/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions",
                   params={"per_page": per_page, "page": page}).json()


@app.get("/list_recent_issues")
def list_recent_issues(filter: str = "assigned", state: str = "all", per_page: int = 30, page: int = 1):
    # /issues는 인증 사용자 관점
    return _gh_get("/issues", params={"filter": filter, "state": state,
                                      "per_page": per_page, "page": page}).json()


@app.get("/search_issues")
def search_issues(q: str, per_page: int = 30, page: int = 1):
    return _gh_get("/search/issues", params={"q": q, "per_page": per_page, "page": page}).json()


# ---------------------------
# 5) Pull Requests
# ---------------------------
@app.get("/fetch_pr")
def fetch_pr(owner: str, repo: str, number: int):
    return _gh_get(f"/repos/{owner}/{repo}/pulls/{number}").json()


@app.get("/fetch_pr_comments")
def fetch_pr_comments(owner: str, repo: str, number: int, per_page: int = 100, page: int = 1):
    return _gh_get(f"/repos/{owner}/{repo}/pulls/{number}/comments",
                   params={"per_page": per_page, "page": page}).json()


@app.get("/fetch_pr_patch", response_class=PlainTextResponse)
def fetch_pr_patch(owner: str, repo: str, number: int):
    r = _gh_get(f"/repos/{owner}/{repo}/pulls/{number}", accept="application/vnd.github.v3.patch")
    return r.text


@app.get("/get_pr_diff", response_class=PlainTextResponse)
def get_pr_diff(owner: str, repo: str, number: int):
    r = _gh_get(f"/repos/{owner}/{repo}/pulls/{number}", accept="application/vnd.github.v3.diff")
    return r.text


@app.get("/fetch_pr_file_patch")
def fetch_pr_file_patch(owner: str, repo: str, number: int, per_page: int = 100, page: int = 1):
    files = _gh_get(f"/repos/{owner}/{repo}/pulls/{number}/files",
                    params={"per_page": per_page, "page": page}).json()
    # 각 파일 JSON에 'patch' 필드 포함
    return files


@app.get("/list_pr_changed_filenames")
def list_pr_changed_filenames(owner: str, repo: str, number: int, per_page: int = 100, page: int = 1):
    files = _gh_get(f"/repos/{owner}/{repo}/pulls/{number}/files",
                    params={"per_page": per_page, "page": page}).json()
    return [f["filename"] for f in files]


@app.get("/search_prs")
def search_prs(q: str, per_page: int = 30, page: int = 1):
    # PR 검색은 /search/issues 를 사용 (is:pr 포함)
    return _gh_get("/search/issues", params={"q": q, "per_page": per_page, "page": page}).json()


# ---------------------------
# 6) 사용자/조직
# ---------------------------
@app.get("/get_profile")
def get_profile():
    return _gh_get("/user").json()


@app.get("/get_user_login")
def get_user_login():
    return {"login": _gh_get("/user").json().get("login")}


@app.get("/list_user_org_memberships")
def list_user_org_memberships(per_page: int = 100, page: int = 1):
    return _gh_get("/user/memberships/orgs", params={"per_page": per_page, "page": page}).json()


@app.get("/list_user_orgs")
def list_user_orgs(per_page: int = 100, page: int = 1):
    return _gh_get("/user/orgs", params={"per_page": per_page, "page": page}).json()


@app.get("/list_installations")
def list_installations(per_page: int = 100, page: int = 1):
    return _gh_get("/user/installations", params={"per_page": per_page, "page": page}).json()


@app.get("/list_installed_accounts")
def list_installed_accounts(per_page: int = 100, page: int = 1):
    return _gh_get("/user/installations", params={"per_page": per_page, "page": page}).json()


# ---------------------------
# 7) 기타
# ---------------------------
@app.get("/fetch_user_content")
def fetch_user_content(owner: str, repo: str, path: str, ref: Optional[str] = None):
    # fetch_file과 동일 (별칭)
    return fetch_file(owner=owner, repo=repo, path=path, ref=ref)


# (선택) Streaming 검색: 서버 센트 이벤트(단순 라인 스트림)
@app.get("/search_installed_repositories_streaming")
def search_installed_repositories_streaming(q: str = ""):
    def gen():
        repos = _gh_get("/installation/repositories", params={"per_page": 100}).json().get("repositories", [])
        for r in repos:
            name = r.get("full_name","")
            if not q or q.lower() in name.lower():
                yield (name + "\n")
    return StreamingResponse(gen(), media_type="text/plain")


# 헬스체크
@app.get("/healthz")
def healthz():
    return {"ok": True}

