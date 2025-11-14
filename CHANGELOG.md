# 변경 사항

## [2025-11-14] 우측 실시간 동기화 패치

### ✅ 완료

1. **좌측 드래그 ↔ 우측 pixel_view 실시간 동기화**
   - `ui/color_definition.py`에 `current_pixel_map` 멤버 추가
   - `MouseMove` 이벤트에서 우측에도 동일 좌표로 드래그 경로 오버레이
   - 좌측과 우측이 실시간으로 동기화되어 드래그 경로가 양쪽 모두 표시됨

2. **requirements.txt 생성**
   - 핵심 의존성 정리 (PyQt5, opencv-python, numpy, pypylon)
   - 선택적 의존성은 `requirements-optional.txt`에 유지

3. **Git 브랜치 자동 감지 개선**
   - `sync_realtime.py`가 현재 브랜치를 자동으로 감지하도록 수정
   - 하드코딩된 `main` 브랜치 제거

4. **GitHub Bridge 기능 확장**
   - `fetch_for_ai.py`에 `--all-files` 옵션 추가 (모든 파일 자동 탐색)
   - GUI에 "Get All Files" 버튼 추가
   - 자동 파일 탐색 기능 개선

### 🔧 개선 사항

- GitHub 기본 브랜치 관련 문서 업데이트
- 브랜치별 자동 동기화 지원
- 파일 탐색 자동화 기능 강화

