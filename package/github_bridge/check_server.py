# package/github_bridge/check_server.py
"""서버 상태 및 토큰 확인 스크립트"""
import os
import sys
import httpx
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

def check_token():
    """토큰 설정 확인"""
    print("=" * 60)
    print("GitHub 토큰 확인")
    print("=" * 60)
    
    token = os.getenv("GITHUB_TOKEN")
    if token:
        masked_token = token[:7] + "..." + token[-4:] if len(token) > 11 else "***"
        print(f"[OK] GITHUB_TOKEN 설정됨: {masked_token}")
        return True
    else:
        print("[오류] GITHUB_TOKEN이 설정되지 않았습니다.")
        print("\n설정 방법:")
        print("  PowerShell:")
        print("    $env:GITHUB_TOKEN = 'ghp_여기에_토큰'")
        print("\n  또는 영구 설정:")
        print("    [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_xxx', 'User')")
        print("\n  토큰 생성:")
        print("    https://github.com/settings/tokens/new")
        return False

def check_server():
    """서버 상태 확인"""
    print("\n" + "=" * 60)
    print("서버 상태 확인")
    print("=" * 60)
    
    try:
        response = httpx.get("http://localhost:8787/healthz", timeout=5.0)
        if response.status_code == 200:
            print("[OK] 서버가 실행 중입니다.")
            return True
        else:
            print(f"[경고] 서버 응답: {response.status_code}")
            return False
    except httpx.ConnectError:
        print("[오류] 서버에 연결할 수 없습니다.")
        print("      서버를 시작하세요: package\\github_bridge\\run_server.bat")
        return False
    except Exception as e:
        print(f"[오류] 서버 확인 중 오류: {e}")
        return False

def test_api():
    """API 테스트"""
    print("\n" + "=" * 60)
    print("API 테스트")
    print("=" * 60)
    
    try:
        response = httpx.get(
            "http://localhost:8787/get_repo",
            params={"owner": "HENRY9300807", "repo": "vision-sorter"},
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[성공] 레포지토리 정보 가져오기 성공")
            print(f"      이름: {data.get('full_name')}")
            print(f"      설명: {data.get('description', 'N/A')}")
            return True
        else:
            print(f"[오류] API 응답: {response.status_code}")
            print(f"      내용: {response.text[:200]}")
            return False
    except httpx.HTTPStatusError as e:
        print(f"[오류] HTTP 에러: {e.response.status_code}")
        print(f"      내용: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"[오류] API 테스트 중 오류: {e}")
        return False

if __name__ == "__main__":
    print("GitHub Bridge 서버 상태 확인\n")
    
    token_ok = check_token()
    server_ok = check_server()
    
    if token_ok and server_ok:
        api_ok = test_api()
        if api_ok:
            print("\n" + "=" * 60)
            print("[성공] 모든 확인 완료!")
        else:
            print("\n" + "=" * 60)
            print("[실패] API 테스트 실패 - 서버를 재시작하세요")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("[실패] 설정이 완료되지 않았습니다.")
        sys.exit(1)

