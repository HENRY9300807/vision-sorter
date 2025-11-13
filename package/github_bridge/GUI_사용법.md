# GitHub Repository Fetcher GUI 사용법

## 실행 방법

### 방법 1: 배치 파일 실행 (Windows)
```bash
package\github_bridge\run_gui.bat
```

### 방법 2: 직접 실행
```bash
python package\github_bridge\gui_fetch.py
```

## 사용 단계

### 1. 레포지토리 정보 입력
- **Owner**: 레포지토리 소유자 (예: `HENRY9300807`)
- **Repository**: 레포지토리 이름 (예: `vision-sorter`)

### 2. 파일 추가
- **File Path** 입력란에 파일 경로 입력 (예: `main.py`)
- **Add** 버튼 클릭하여 목록에 추가
- 여러 파일을 추가하려면 반복

### 3. 이슈 옵션 설정
- **Include Issues**: 이슈 포함 여부 체크
- **Max Issues**: 가져올 최대 이슈 개수 (1-1000)

### 4. 정보 가져오기
- **Fetch Repository Info** 버튼 클릭
- 진행 상태가 표시됩니다

### 5. 결과 사용
- **Save to File**: 텍스트 파일로 저장
- **Copy to Clipboard**: 클립보드에 복사 (ChatGPT/Cursor AI에 붙여넣기)

## 예시 사용 시나리오

### ChatGPT에 제공하기
1. Owner: `HENRY9300807`, Repository: `vision-sorter` 입력
2. 파일 추가:
   - `main.py`
   - `package/capture_96_limit.py`
   - `package/image_utils.py`
3. Include Issues 체크, Max Issues: 20
4. **Fetch Repository Info** 클릭
5. 완료 후 **Copy to Clipboard** 클릭
6. ChatGPT에 붙여넣기

## 주의사항

- GitHub Bridge 서버가 실행 중이어야 합니다 (`http://localhost:8787`)
- GitHub 토큰이 설정되어 있어야 합니다
- 큰 파일이나 많은 이슈는 시간이 걸릴 수 있습니다

