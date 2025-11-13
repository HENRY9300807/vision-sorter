#!/usr/bin/env python3
"""
파일 저장을 실시간으로 감지하여 자동으로 git add, commit, push를 실행하는 프로그램
"""
import subprocess
import time
import threading
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# === 설정 ===
REPO_ROOT = Path(__file__).resolve().parent.parent
BRANCH = "main"
DEBOUNCE_SEC = 2  # 파일 저장 후 2초 대기 (연속 저장 방지)
IGNORE_PATTERNS = [
    "*.pyc", "__pycache__", ".git", "*.jpg", "*.png", 
    "*.npy", ".venv", "node_modules", "*.log"
]

class GitAutoSyncHandler(FileSystemEventHandler):
    """파일 변경 감지 및 자동 Git 동기화"""
    
    def __init__(self, repo_root: Path, branch: str, debounce_sec: float):
        self.repo_root = repo_root
        self.branch = branch
        self.debounce_sec = debounce_sec
        self.last_commit_time = 0
        self.pending_files = set()
        self.lock = threading.Lock()
        self.timer = None
        
    def should_ignore(self, file_path: Path) -> bool:
        """무시할 파일/디렉토리인지 확인"""
        for pattern in IGNORE_PATTERNS:
            if pattern in str(file_path) or file_path.name.startswith('.'):
                return True
        return False
    
    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # 무시할 파일 체크
        if self.should_ignore(file_path):
            return
        
        # .py, .json, .yaml, .yml 등 소스 파일만 감지
        if file_path.suffix not in ['.py', '.json', '.yaml', '.yml', '.md', '.txt', '.ui']:
            return
        
        with self.lock:
            self.pending_files.add(file_path)
            
            # 타이머 리셋 (debounce)
            if self.timer:
                self.timer.cancel()
            
            # debounce 시간 후 커밋 실행
            self.timer = threading.Timer(self.debounce_sec, self._commit_pending)
            self.timer.start()
    
    def _commit_pending(self):
        """대기 중인 파일들을 커밋하고 푸시"""
        with self.lock:
            if not self.pending_files:
                return
            
            # 너무 자주 커밋하지 않도록 제한 (최소 5초 간격)
            now = time.time()
            if now - self.last_commit_time < 5:
                return
            
            files_to_commit = list(self.pending_files)
            self.pending_files.clear()
            self.last_commit_time = now
        
        # Git 작업 실행
        try:
            self._run_git_sync(files_to_commit)
        except Exception as e:
            print(f"❌ Git 동기화 실패: {e}")
    
    def _run_git_sync(self, changed_files: list):
        """Git add, commit, push 실행"""
        print(f"\n📝 변경된 파일 감지: {len(changed_files)}개")
        for f in changed_files[:5]:  # 최대 5개만 표시
            print(f"   - {f.relative_to(self.repo_root)}")
        if len(changed_files) > 5:
            print(f"   ... 외 {len(changed_files) - 5}개")
        
        # Git 작업 실행
        try:
            # git add
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )
            
            # git commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"auto: sync {timestamp}"
            
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            # 변경사항이 없으면 스킵
            if "nothing to commit" in result.stdout.lower():
                print("   ℹ️  커밋할 변경사항 없음")
                return
            
            # git pull (충돌 방지)
            subprocess.run(
                ["git", "pull", "--rebase", "origin", self.branch],
                cwd=self.repo_root,
                capture_output=True,
                check=False  # pull 실패해도 계속 진행
            )
            
            # git push
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", self.branch],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                print(f"✅ 푸시 완료: {commit_msg}")
            else:
                print(f"⚠️  푸시 실패: {push_result.stderr}")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 명령 실패: {e}")


def main():
    """메인 함수"""
    print("=" * 60)
    print("🚀 Git Auto Sync 시작")
    print(f"📁 레포지토리: {REPO_ROOT}")
    print(f"🌿 브랜치: {BRANCH}")
    print(f"⏱️  Debounce: {DEBOUNCE_SEC}초")
    print("=" * 60)
    print("\n💡 파일을 저장하면 자동으로 git add → commit → push 됩니다")
    print("🛑 중지하려면 Ctrl+C를 누르세요\n")
    
    # Git 레포지토리 확인
    if not (REPO_ROOT / ".git").exists():
        print("❌ Git 레포지토리가 아닙니다!")
        return
    
    # 이벤트 핸들러 생성
    event_handler = GitAutoSyncHandler(REPO_ROOT, BRANCH, DEBOUNCE_SEC)
    
    # 파일 감시 시작
    observer = Observer()
    observer.schedule(event_handler, str(REPO_ROOT), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 중지 요청 받음...")
        observer.stop()
    
    observer.join()
    print("👋 종료되었습니다")


if __name__ == "__main__":
    main()

