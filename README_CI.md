# CI 및 로컬 실행 가이드

## CI (GitHub Actions)

CI는 헤드리스 환경에서 다음만 수행합니다:

- ✅ **의존성 검증**: 필수 모듈 import 확인
- ✅ **정적 검사**: ruff 린터
- ✅ **스모크 테스트**: 기본 import 동작 확인
- ❌ **GUI 실행**: CI에서는 실행하지 않음 (디스플레이 없음)
- ❌ **카메라/하드웨어**: CI에서는 접근 불가

### CI 워크플로

`.github/workflows/ci.yml`이 다음을 수행합니다:

1. Python 3.11 환경 설정
2. 의존성 설치 (requirements.txt + CI 전용 패키지)
3. Qt 오프스크린 플랫폼 설정
4. ruff 린터 실행
5. 스모크 테스트 (`tools/smoke_imports.py`)
6. 테스트 실행 (tests/ 디렉토리가 있으면)

## 로컬 실행

로컬(개발 PC)에서 GUI와 하드웨어를 사용하여 실행:

### 1. 의존성 설치

```bash
# 가상환경 활성화 (권장)
.venv\Scripts\activate  # Windows
# 또는
source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
```

### 2. 프로그램 실행

```bash
# 메인 프로그램 실행 (GUI + 카메라)
python main.py
```

### 3. 데모 실행

```bash
# 스크리블 동기화 데모
python ui/demo_scribble_sync_qt.py
```

## CI vs 로컬 차이점

| 항목 | CI (GitHub Actions) | 로컬 (개발 PC) |
|------|---------------------|----------------|
| GUI | ❌ 오프스크린 모드 | ✅ 정상 실행 |
| 카메라 | ❌ 사용 불가 | ✅ 정상 동작 |
| 하드웨어 | ❌ 접근 불가 | ✅ 정상 동작 |
| 린터 | ✅ ruff 실행 | 선택적 |
| 스모크 테스트 | ✅ import 확인 | 선택적 |

## 문제 해결

### CI에서 실패하는 경우

1. **의존성 문제**: `requirements.txt` 확인
2. **Import 오류**: `tools/smoke_imports.py`에서 실패한 모듈 확인
3. **린터 오류**: `ruff check .` 로컬에서 실행하여 확인

### 로컬에서 실행 안 되는 경우

1. **가상환경 확인**: 올바른 Python 환경 사용 중인지 확인
2. **패키지 설치**: `pip install -r requirements.txt`
3. **카메라 접근**: 다른 프로그램이 카메라를 사용 중인지 확인

## 다음 단계 (선택)

- `--selftest` 모드 추가: 샘플 이미지를 받아 비UI 경로로 전처리/분류만 수행
- `pytest -m "not hardware"` 마커로 하드웨어 의존 테스트 제외
- `ruff format`/`mypy` 추가로 정적 품질 강화

