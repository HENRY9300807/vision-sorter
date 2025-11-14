# package/github_bridge/sync_realtime.py
"""
GitHub 레포지토리와 로컬 디렉토리 실시간 동기화 스크립트

로컬 파일 변경사항을 자동으로 감지하여 GitHub에 푸시하고,
GitHub의 변경사항도 주기적으로 가져옵니다.
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from typing import Set, Optional, List, Tuple
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("watchdog 패키지가 필요합니다. 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent

# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).resolve().parents[2]
GIT_DIR = ROOT_DIR / ".git"

# 무시할 파일/디렉토리 패턴
IGNORE_PATTERNS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
}


class GitSyncHandler(FileSystemEventHandler):
    """파일 시스템 변경사항을 감지하고 Git에 커밋/푸시하는 핸들러"""
    
    def __init__(self, sync_interval: int = 5, auto_push: bool = True, auto_pull: bool = True, pull_interval: int = 60):
        super().__init__()
        self.sync_interval = sync_interval  # 변경사항을 모아서 커밋할 시간(초)
        self.auto_push = auto_push
        self.auto_pull = auto_pull
        self.pull_interval = pull_interval  # GitHub에서 가져올 주기(초)
        
        self.changed_files: Set[str] = set()
        self.last_sync_time = time.time()
        self.last_pull_time = time.time()
        self.lock = threading.Lock()
        
        # 백그라운드 스레드에서 주기적으로 동기화
        self.sync_thread = threading.Thread(target=self._periodic_sync, daemon=True)
        self.sync_thread.start()
        
        # 백그라운드 스레드에서 주기적으로 pull
        if self.auto_pull:
            self.pull_thread = threading.Thread(target=self._periodic_pull, daemon=True)
            self.pull_thread.start()
    
    def _should_ignore(self, path: str) -> bool:
        """파일/디렉토리를 무시해야 하는지 확인"""
        path_lower = path.lower()
        for pattern in IGNORE_PATTERNS:
            if pattern.startswith("*"):
                if path_lower.endswith(pattern[1:]):
                    return True
            elif pattern in path_lower:
                return True
        return False
    
    def on_modified(self, event: FileSystemEvent):
        """파일이 수정되었을 때"""
        if not event.is_directory:
            self._handle_change(event.src_path)
    
    def on_created(self, event: FileSystemEvent):
        """파일이 생성되었을 때"""
        if not event.is_directory:
            self._handle_change(event.src_path)
    
    def on_deleted(self, event: FileSystemEvent):
        """파일이 삭제되었을 때"""
        if not event.is_directory:
            self._handle_change(event.src_path)
    
    def on_moved(self, event: FileSystemEvent):
        """파일이 이동되었을 때"""
        if not event.is_directory:
            self._handle_change(event.src_path)
            if hasattr(event, 'dest_path'):
                self._handle_change(event.dest_path)
    
    def _handle_change(self, file_path: str):
        """변경사항 처리"""
        if self._should_ignore(file_path):
            return
        
        # 상대 경로로 변환
        try:
            rel_path = os.path.relpath(file_path, ROOT_DIR)
        except ValueError:
            return  # 다른 드라이브의 파일은 무시
        
        with self.lock:
            self.changed_files.add(rel_path)
            print(f"[변경 감지] {rel_path}")
    
    def _periodic_sync(self):
        """주기적으로 변경사항을 Git에 커밋/푸시"""
        while True:
            time.sleep(self.sync_interval)
            
            with self.lock:
                if self.changed_files and time.time() - self.last_sync_time >= self.sync_interval:
                    files_to_commit = list(self.changed_files)
                    self.changed_files.clear()
                    self.last_sync_time = time.time()
                else:
                    files_to_commit = []
            
            if files_to_commit:
                self._commit_and_push(files_to_commit)
    
    def _periodic_pull(self):
        """주기적으로 GitHub에서 변경사항을 가져옴"""
        while True:
            time.sleep(self.pull_interval)
            if time.time() - self.last_pull_time >= self.pull_interval:
                self._pull_from_github()
                self.last_pull_time = time.time()
    
    def _run_git_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """Git 명령어 실행"""
        try:
            if cwd is None:
                cwd = ROOT_DIR
            result = subprocess.run(
                ["git"] + cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def _get_current_branch(self) -> str:
        """현재 Git 브랜치 이름 가져오기"""
        success, output = self._run_git_command(["branch", "--show-current"])
        if success and output.strip():
            return output.strip()
        # fallback: symbolic-ref 사용
        success, output = self._run_git_command(["symbolic-ref", "--short", "HEAD"])
        if success and output.strip():
            return output.strip()
        # 최후의 수단: 기본값
        return "main"
    
    def _commit_and_push(self, files: List[str]):
        """변경된 파일들을 커밋하고 푸시"""
        if not files:
            return
        
        print(f"\n[동기화 시작] {len(files)}개 파일 커밋 중...")
        
        # Git 상태 확인
        success, output = self._run_git_command(["status", "--porcelain"])
        if not success:
            print(f"[오류] Git 상태 확인 실패: {output}")
            return
        
        # 변경사항이 없으면 스킵
        if not output.strip():
            return
        
        # 모든 변경사항 추가
        success, output = self._run_git_command(["add", "-A"])
        if not success:
            print(f"[오류] Git add 실패: {output}")
            return
        
        # 커밋 메시지 생성
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto-sync: {len(files)} files changed at {timestamp}"
        
        # 커밋
        success, output = self._run_git_command(["commit", "-m", commit_msg])
        if not success:
            if "nothing to commit" in output.lower():
                print("[정보] 커밋할 변경사항이 없습니다.")
                return
            print(f"[오류] Git commit 실패: {output}")
            return
        
        print(f"[성공] 커밋 완료: {commit_msg}")
        
        # 푸시
        if self.auto_push:
            current_branch = self._get_current_branch()
            success, output = self._run_git_command(["push", "origin", current_branch])
            
            if success:
                print(f"[성공] GitHub에 푸시 완료 (브랜치: {current_branch})")
            else:
                print(f"[경고] GitHub 푸시 실패: {output}")
                print("      나중에 수동으로 'git push'를 실행하세요.")
    
    def _pull_from_github(self):
        """GitHub에서 변경사항을 가져옴"""
        print("\n[동기화] GitHub에서 변경사항 확인 중...")
        
        # fetch 먼저
        success, output = self._run_git_command(["fetch", "origin"])
        if not success:
            print(f"[오류] Git fetch 실패: {output}")
            return
        
        # 현재 브랜치 가져오기
        current_branch = self._get_current_branch()
        remote_branch = f"origin/{current_branch}"
        
        # 로컬과 원격의 차이 확인
        success, output = self._run_git_command(["log", f"HEAD..{remote_branch}", "--oneline"])
        
        if output.strip():
            print(f"[발견] GitHub에 새로운 변경사항이 있습니다: {len(output.strip().split(chr(10)))}개 커밋")
            print("[동기화] 변경사항 가져오는 중...")
            
            # pull
            success, output = self._run_git_command(["pull", "origin", current_branch, "--no-edit"])
            
            if success:
                print(f"[성공] GitHub에서 변경사항 가져오기 완료 (브랜치: {current_branch})")
            else:
                print(f"[경고] Git pull 실패: {output}")
                print("      충돌이 있을 수 있습니다. 수동으로 확인하세요.")
        else:
            print("[정보] GitHub에 새로운 변경사항이 없습니다.")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub 레포지토리와 로컬 디렉토리 실시간 동기화")
    parser.add_argument("--sync-interval", type=int, default=5,
                       help="변경사항을 모아서 커밋할 시간(초) (기본값: 5)")
    parser.add_argument("--pull-interval", type=int, default=60,
                       help="GitHub에서 변경사항을 가져올 주기(초) (기본값: 60)")
    parser.add_argument("--no-push", action="store_true",
                       help="자동 푸시 비활성화 (커밋만 수행)")
    parser.add_argument("--no-pull", action="store_true",
                       help="자동 pull 비활성화")
    
    args = parser.parse_args()
    
    # Git 저장소 확인
    if not GIT_DIR.exists():
        print(f"[오류] {ROOT_DIR}는 Git 저장소가 아닙니다.")
        print("      먼저 'git init'을 실행하세요.")
        return 1
    
    # 원격 저장소 확인
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if result.returncode != 0 or not result.stdout.strip():
            print("[경고] 원격 저장소가 설정되지 않았습니다.")
            print("      'git remote add origin <URL>'로 설정하세요.")
    except Exception:
        print("[경고] 원격 저장소 확인 중 오류가 발생했습니다.")
    
    print("=" * 60)
    print("GitHub 실시간 동기화 시작")
    print("=" * 60)
    print(f"로컬 디렉토리: {ROOT_DIR}")
    print(f"동기화 간격: {args.sync_interval}초")
    print(f"Pull 간격: {args.pull_interval}초")
    print(f"자동 푸시: {'비활성화' if args.no_push else '활성화'}")
    print(f"자동 Pull: {'비활성화' if args.no_pull else '활성화'}")
    print("=" * 60)
    print("\n파일 변경사항을 감시 중... (Ctrl+C로 종료)\n")
    
    # 이벤트 핸들러 생성
    event_handler = GitSyncHandler(
        sync_interval=args.sync_interval,
        auto_push=not args.no_push,
        auto_pull=not args.no_pull,
        pull_interval=args.pull_interval
    )
    
    # Observer 생성 및 시작
    observer = Observer()
    observer.schedule(event_handler, str(ROOT_DIR), recursive=True)
    observer.start()
    
    try:
        # 초기 pull
        if not args.no_pull:
            event_handler._pull_from_github()
        
        # 무한 대기
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[종료] 동기화를 중지합니다...")
        observer.stop()
    
    observer.join()
    print("[완료] 동기화가 종료되었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

