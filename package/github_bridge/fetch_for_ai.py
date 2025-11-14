# package/github_bridge/fetch_for_ai.py
"""
GitHub 레포지토리의 파일과 이슈를 가져와서 AI에게 제공할 수 있는 형태로 출력
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx

BASE_URL = "http://localhost:8787"


def fetch_repo_info(owner: str, repo: str) -> Dict[str, Any]:
    """레포지토리 정보 가져오기"""
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/get_repo", params={"owner": owner, "repo": repo})
        r.raise_for_status()
        return r.json()


def fetch_file(owner: str, repo: str, path: str, ref: str = None) -> Dict[str, Any]:
    """파일 내용 가져오기"""
    params = {"owner": owner, "repo": repo, "path": path}
    if ref:
        params["ref"] = ref
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/fetch_file", params=params)
        r.raise_for_status()
        return r.json()


def fetch_issues(owner: str, repo: str, state: str = "all", per_page: int = 100) -> List[Dict[str, Any]]:
    """이슈 목록 가져오기"""
    q = f"repo:{owner}/{repo} is:issue state:{state}"
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/search_issues", params={"q": q, "per_page": per_page})
        r.raise_for_status()
        return r.json().get("items", [])


def fetch_issue_detail(owner: str, repo: str, number: int) -> Dict[str, Any]:
    """이슈 상세 정보 가져오기"""
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/fetch_issue", params={"owner": owner, "repo": repo, "number": number})
        r.raise_for_status()
        return r.json()


def get_file_tree(owner: str, repo: str, path: str = "", ref: str = None) -> List[Dict[str, Any]]:
    """디렉토리 트리 가져오기"""
    params = {"owner": owner, "repo": repo, "path": path}
    if ref:
        params["ref"] = ref
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/fetch_file", params=params)
        r.raise_for_status()
        result = r.json()
        if result.get("type") == "dir":
            return result.get("entries", [])
        return []


def format_for_ai(owner: str, repo: str, files: List[str] = None, issues: bool = True, max_issues: int = 50):
    """AI에게 제공할 형태로 포맷팅"""
    import io
    # Windows에서 UTF-8 출력 설정
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    output = []
    
    # 레포지토리 정보
    output.append(f"# GitHub Repository: {owner}/{repo}\n\n")
    repo_info = fetch_repo_info(owner, repo)
    output.append(f"## Repository Information\n")
    output.append(f"- Name: {repo_info.get('full_name')}\n")
    output.append(f"- Description: {repo_info.get('description', 'N/A')}\n")
    output.append(f"- Default Branch: {repo_info.get('default_branch')}\n")
    output.append(f"- Stars: {repo_info.get('stargazers_count')}\n")
    output.append(f"- Issues: {repo_info.get('open_issues_count')}\n")
    output.append(f"\n")
    
    # 파일 내용
    if files:
        output.append(f"## File Contents\n\n")
        default_branch = repo_info.get("default_branch", "main")
        
        for file_path in files:
            try:
                file_data = fetch_file(owner, repo, file_path, default_branch)
                if file_data.get("type") == "file":
                    content = file_data.get("decoded", "")
                    output.append(f"### {file_path}\n\n")
                    output.append("```\n")
                    output.append(content)
                    output.append("\n```\n\n")
                else:
                    output.append(f"### {file_path}\n\n")
                    output.append(f"(Directory or file cannot be read)\n\n")
            except Exception as e:
                output.append(f"### {file_path}\n\n")
                output.append(f"Error: {e}\n\n")
    
    # 이슈 목록
    if issues:
        output.append(f"## Issues\n\n")
        try:
            issue_list = fetch_issues(owner, repo, state="all", per_page=max_issues)
            output.append(f"Total Issues: {len(issue_list)}\n\n")
            
            for issue in issue_list[:max_issues]:
                number = issue.get("number")
                title = issue.get("title", "N/A")
                state = issue.get("state", "N/A")
                created = issue.get("created_at", "N/A")
                labels = [l.get("name") for l in issue.get("labels", [])]
                
                output.append(f"### Issue #{number}: {title}\n")
                output.append(f"- State: {state}\n")
                output.append(f"- Created: {created}\n")
                if labels:
                    output.append(f"- Labels: {', '.join(labels)}\n")
                output.append(f"- URL: {issue.get('html_url')}\n")
                
                # 이슈 본문 (간단히)
                body = issue.get("body", "")
                if body:
                    body_preview = body[:200] + "..." if len(body) > 200 else body
                    output.append(f"- Body Preview: {body_preview}\n")
                output.append(f"\n")
        except Exception as e:
            output.append(f"Error fetching issues: {e}\n\n")
    
    return "".join(output)


def get_all_files(owner: str, repo: str, path: str = "", ref: str = None) -> List[str]:
    """모든 파일 목록 재귀적으로 탐색"""
    if ref is None:
        ref = fetch_repo_info(owner, repo).get("default_branch", "main")
    
    all_files = []
    ignore_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", 
                   "node_modules", ".idea", ".vscode", "dist", "build", ".env"}
    ignore_extensions = {".pyc", ".pyo", ".pyd", ".so", ".swp", ".swo", "~", ".DS_Store", 
                        ".Thumbs.db", ".zip"}
    
    def scan_directory(dir_path: str):
        try:
            entries = get_file_tree(owner, repo, dir_path, ref)
            for entry in entries:
                name = entry.get("name", "")
                entry_type = entry.get("type", "")
                entry_path = f"{dir_path}/{name}" if dir_path else name
                
                # 디렉토리인 경우
                if entry_type == "dir":
                    if name not in ignore_dirs and not name.startswith("."):
                        scan_directory(entry_path)
                # 파일인 경우
                elif entry_type == "file":
                    # 무시할 확장자 확인
                    should_ignore = False
                    for ext in ignore_extensions:
                        if name.endswith(ext):
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        all_files.append(entry_path)
        except Exception as e:
            print(f"Warning: Cannot scan directory {dir_path}: {e}", file=sys.stderr)
    
    scan_directory(path)
    return sorted(all_files)


def get_default_files(owner: str, repo: str) -> List[str]:
    """기본 파일 목록 자동 탐색"""
    default_branch = fetch_repo_info(owner, repo).get("default_branch", "main")
    default_files = []
    
    # 루트 디렉토리에서 주요 파일 찾기
    try:
        root_files = get_file_tree(owner, repo, "", default_branch)
        # 우선순위가 높은 파일들
        priority_extensions = [".py", ".md", ".txt", ".yml", ".yaml", ".json"]
        priority_names = ["main.py", "README.md", "requirements.txt", "setup.py"]
        
        for file_info in root_files:
            name = file_info.get("name", "")
            if name in priority_names:
                default_files.append(name)
        
        # 추가로 .py 파일 2-3개
        py_files = [f.get("name") for f in root_files if f.get("name", "").endswith(".py") and f.get("name") not in default_files]
        default_files.extend(py_files[:3])
        
        # 중복 제거 및 순서 유지
        seen = set()
        result = []
        for f in default_files:
            if f and f not in seen:
                seen.add(f)
                result.append(f)
        
        return result[:5]  # 최대 5개만
    except Exception:
        # 기본값
        return ["main.py"]
    

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub 레포지토리 파일과 이슈를 AI용으로 가져오기")
    parser.add_argument("--owner", default="HENRY9300807", help="레포지토리 소유자")
    parser.add_argument("--repo", default="vision-sorter", help="레포지토리 이름")
    parser.add_argument("--files", nargs="+", help="가져올 파일 경로 (예: main.py package/capture_96_limit.py)")
    parser.add_argument("--all-files", action="store_true", help="브랜치의 모든 파일 가져오기 (재귀적 탐색)")
    parser.add_argument("--auto-files", action="store_true", default=True, help="파일 미지정 시 자동으로 주요 파일 가져오기 (기본값: True)")
    parser.add_argument("--no-auto-files", dest="auto_files", action="store_false", help="자동 파일 탐색 비활성화")
    parser.add_argument("--no-issues", action="store_true", help="이슈 목록 제외")
    parser.add_argument("--max-issues", type=int, default=50, help="최대 이슈 개수")
    parser.add_argument("--output", help="출력 파일 경로 (없으면 stdout)")
    
    args = parser.parse_args()
    
    # 파일 목록 결정
    files = args.files
    if args.all_files:
        print("브랜치의 모든 파일을 탐색합니다...", file=sys.stderr)
        try:
            files = get_all_files(args.owner, args.repo)
            if files:
                print(f"✅ {len(files)}개 파일 발견", file=sys.stderr)
                print(f"파일 목록: {', '.join(files[:10])}{' ...' if len(files) > 10 else ''}", file=sys.stderr)
            else:
                print("경고: 파일을 찾을 수 없습니다.", file=sys.stderr)
        except Exception as e:
            print(f"전체 파일 탐색 실패: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    elif not files and args.auto_files:
        print("파일을 지정하지 않았습니다. 자동으로 주요 파일을 탐색합니다...", file=sys.stderr)
        try:
            files = get_default_files(args.owner, args.repo)
            if files:
                print(f"자동 탐색된 파일: {', '.join(files)}", file=sys.stderr)
            else:
                print("경고: 자동으로 파일을 찾을 수 없습니다. --files 옵션으로 파일을 지정하세요.", file=sys.stderr)
        except Exception as e:
            print(f"자동 파일 탐색 실패: {e}", file=sys.stderr)
            print("--files 옵션으로 파일을 직접 지정하세요.", file=sys.stderr)
    
    try:
        result = format_for_ai(
            owner=args.owner,
            repo=args.repo,
            files=files,
            issues=not args.no_issues,
            max_issues=args.max_issues
        )
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"Result saved to {args.output}", file=sys.stderr)
        else:
            print(result, end="")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

