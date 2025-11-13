# Git 자동 동기화 프로그램

파일을 저장할 때마다 자동으로 `git add → commit → push`를 실행하는 프로그램입니다.

## 설치

```bash
pip install watchdog
```

또는

```bash
pip install -r requirements-dev.txt
```

## 사용 방법

### Windows
```bash
tools\run_auto_git_sync.bat
```

또는 직접 실행:
```bash
python tools/auto_git_sync.py
```

### Linux/Mac
```bash
chmod +x tools/run_auto_git_sync.sh
./tools/run_auto_git_sync.sh
```

## 동작 방식

1. **파일 감시**: 프로젝트 폴더의 모든 파일 변경을 실시간으로 감지
2. **Debounce**: 파일 저장 후 2초 대기 (연속 저장 방지)
3. **자동 커밋**: 변경된 파일을 자동으로 `git add -A`
4. **자동 푸시**: 커밋 메시지와 함께 자동으로 `git push`

## 설정 변경

`tools/auto_git_sync.py` 파일에서 다음 설정을 변경할 수 있습니다:

```python
BRANCH = "main"           # 브랜치 이름
DEBOUNCE_SEC = 2          # 파일 저장 후 대기 시간 (초)
IGNORE_PATTERNS = [...]   # 무시할 파일 패턴
```

## 주의사항

- ⚠️ **자동 커밋**: 모든 변경사항이 자동으로 커밋되므로, 테스트 코드나 임시 파일은 주의하세요
- ⚠️ **충돌 처리**: 원격에 변경사항이 있으면 자동으로 pull을 시도하지만, 충돌 시 수동 해결 필요
- ⚠️ **최소 간격**: 5초 이내에는 다시 커밋하지 않습니다 (너무 자주 커밋하는 것 방지)

## 중지 방법

프로그램 실행 중 `Ctrl+C`를 누르면 중지됩니다.

