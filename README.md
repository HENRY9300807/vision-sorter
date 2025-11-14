# Vision Sorter - 색상 기반 비전 분류 라벨링 툴

Basler 카메라로 캡처한 이미지를 실시간으로 라벨링하고, RGB 색상 구(Sphere) 기반으로 픽셀을 자동 분류하는 PyQt5 애플리케이션입니다.

## 주요 기능

- 🎨 **실시간 라벨링**: 좌측 원본 이미지에서 드래그하여 색상 영역 선택
- 🔄 **양방향 동기화**: 좌측 드래그 경로가 우측 분류맵에도 실시간 반영
- 🎯 **자동 분류**: RGB 구(Sphere) 기반 벡터화 픽셀 분류
- 📷 **자동 캡처**: Basler 카메라로 자동 이미지 캡처 (100장 루프)
- 💾 **색상 정의 저장**: JSON 형태로 색상 구 정의 저장/로드

## 설치

### 필수 의존성

```powershell
pip install -r requirements.txt
```

필수 패키지:
- PyQt5 (GUI)
- opencv-python (이미지 처리)
- numpy (수치 계산)
- pypylon (Basler 카메라)

### 선택적 의존성 (GitHub Bridge 등)

```powershell
pip install -r requirements-optional.txt
```

## 사용법

### 기본 실행

```powershell
python main.py
```

### 라벨링 프로세스

1. **라벨 선택**: Product / Defect / Background 중 선택
2. **드래그**: 좌측 원본 이미지에서 색상 영역 드래그
   - 좌측: 빨간 점으로 드래그 경로 표시
   - 우측: 분류맵에도 동일 좌표로 빨간 점 표시 (실시간 동기화)
3. **Release**: 마우스를 떼면
   - 좌측: 선택한 RGB 영역이 초록으로 하이라이트
   - 우측: 분류맵에서도 해당 RGB 영역이 초록으로 강조
4. **Save**: 임시 저장된 RGB를 색상 구(Sphere)로 등록하고 저장
   - 우측 분류맵이 즉시 갱신됨 (새로운 구 반영)

## 프로젝트 구조

```
analysis_color/
├── main.py                      # 앱 진입점
├── ui/
│   ├── color_definition.py      # PyQt5 GUI (PhotoViewer)
│   └── mainwindow.ui            # UI 디자인 파일
├── package/
│   ├── capture_96_limit.py      # Basler 카메라 캡처 스크립트
│   ├── color_utils.py           # RGB 구 저장/로드/분류
│   ├── image_utils.py           # 픽셀 분류 엔진 (make_pixel_map)
│   ├── operation.py             # 공통 파라미터
│   └── github_bridge/           # GitHub Bridge 서버/도구
├── data/
│   └── color_defs.json          # 색상 정의 저장 파일
├── picture/                     # 캡처된 이미지 저장 폴더
└── requirements.txt             # 필수 의존성
```

## GitHub 동기화

### 자동 동기화 (간단)

```powershell
.\auto-sync.ps1
```

### 자동 동기화 (고급 - 양방향)

```powershell
.\package\github_bridge\run_sync.bat
```

### GitHub Bridge 서버 실행

```powershell
.\package\github_bridge\run_server.bat
```

서버 실행 후: http://localhost:8787/docs

## 브랜치 정보

현재 기본 브랜치: `henry/analysis_color`

모든 스크립트는 현재 브랜치를 자동으로 감지하여 동작합니다.

## 개발 상태

- ✅ 좌측/우측 실시간 드래그 동기화
- ✅ Release 시 양쪽 하이라이트
- ✅ RGB 구 기반 벡터화 분류
- ✅ 자동 캡처 파이프라인
- ✅ GitHub Bridge (파일/이슈 읽기, 자동 동기화)

## 라이선스

MIT

