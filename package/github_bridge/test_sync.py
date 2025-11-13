# package/github_bridge/test_sync.py
"""간단한 동기화 테스트 스크립트"""
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

def test_git():
    """Git 상태 확인"""
    print("=" * 60)
    print("Git 상태 확인")
    print("=" * 60)
    
    # Git 저장소 확인
    if not (ROOT_DIR / ".git").exists():
        print("[오류] Git 저장소가 아닙니다.")
        return False
    
    # 원격 저장소 확인
    result = subprocess.run(
        ["git", "remote", "-v"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    print(f"원격 저장소:\n{result.stdout}")
    
    # 현재 브랜치 확인
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    print(f"현재 브랜치: {result.stdout.strip()}")
    
    # 변경사항 확인
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    changes = [line for line in result.stdout.strip().split('\n') if line]
    print(f"\n변경된 파일 수: {len(changes)}")
    if changes:
        print("변경된 파일 (처음 10개):")
        for line in changes[:10]:
            print(f"  {line}")
    
    return True

def test_sync_script():
    """동기화 스크립트 확인"""
    print("\n" + "=" * 60)
    print("동기화 스크립트 확인")
    print("=" * 60)
    
    sync_file = ROOT_DIR / "package" / "github_bridge" / "sync_realtime.py"
    if not sync_file.exists():
        print("[오류] sync_realtime.py 파일을 찾을 수 없습니다.")
        return False
    
    print(f"[OK] sync_realtime.py 파일 존재")
    
    # watchdog 확인
    try:
        from watchdog import observers
        print("[OK] watchdog 설치됨")
    except ImportError:
        print("[오류] watchdog이 설치되지 않았습니다.")
        print("      설치: pip install watchdog")
        return False
    
    return True

if __name__ == "__main__":
    print("GitHub 실시간 동기화 테스트\n")
    
    git_ok = test_git()
    sync_ok = test_sync_script()
    
    print("\n" + "=" * 60)
    if git_ok and sync_ok:
        print("[성공] 모든 테스트 통과!")
        print("\n실행 방법:")
        print("  python package\\github_bridge\\sync_realtime.py")
        print("  또는")
        print("  package\\github_bridge\\run_sync.bat")
    else:
        print("[실패] 일부 테스트 실패")
        sys.exit(1)

