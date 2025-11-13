# 스크리블 동기화 기능

왼쪽 원본 이미지에 브러시로 칠하면 오른쪽(축소/픽셀화) 이미지에도 동일 위치로 실시간 동기화하는 기능입니다.

## 파일 구조

- `ui/scribble_sync.py` - 메인 클래스 (`ScribbleView`, `link_views`)
- `ui/demo_scribble_sync_qt.py` - 독립 실행 데모
- `tools/scribble_sync_cv.py` - OpenCV 버전 (빠른 테스트용)

## 빠른 시작

### 1. 데모 실행

```bash
# 이미지 파일이 있는 경우
python ui/demo_scribble_sync_qt.py

# 환경 변수로 이미지 경로 지정
set LEFT_IMG=picture\frame_000.jpg
set RIGHT_IMG=picture\frame_001.jpg
python ui/demo_scribble_sync_qt.py
```

### 2. 기존 PhotoViewer에 통합

`ui/color_definition.py`의 `PhotoViewer` 클래스에서:

```python
from ui.scribble_sync import ScribbleView, link_views

# 기존 QGraphicsView 대신 ScribbleView 사용
# 또는 기존 뷰를 ScribbleView로 래핑
```

## 주요 기능

- ✅ **정확한 좌표 매핑**: QGraphicsView의 `mapToScene` → `mapFromScene` 사용
- ✅ **자동 스케일링**: 브러시 크기가 상대 이미지 크기에 맞춰 자동 조정
- ✅ **줌/패닝 지원**: 확대/축소/스크롤해도 정확한 매핑 유지
- ✅ **실시간 동기화**: 드래그하는 동안 실시간으로 양쪽 뷰에 표시

## API

### ScribbleView

```python
view = ScribbleView(base_image)  # QImage 필요

# 브러시 설정
view.set_brush(radius=10, color=QColor(255, 0, 0, 200))

# 오버레이 지우기
view.clear_overlay()

# 파트너 설정 (동기화)
view.set_partner(other_view)
```

### link_views

```python
left_view = ScribbleView(left_image)
right_view = ScribbleView(right_image)
link_views(left_view, right_view)  # 양방향 동기화
```

## 통합 예시

기존 `PhotoViewer`에 통합하려면:

```python
# ui/color_definition.py 수정 예시
from ui.scribble_sync import ScribbleView, link_views

class PhotoViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        # ... 기존 코드 ...
        
        # 기존 QGraphicsView를 ScribbleView로 교체
        if self.current_img is not None:
            left_img = self.current_img  # numpy array
            # numpy array를 QImage로 변환
            qimg = self._numpy_to_qimage(left_img)
            
            # ScribbleView 생성
            self.scribble_left = ScribbleView(qimg)
            self.scribble_right = ScribbleView(pixelized_qimg)
            
            # 동기화 연결
            link_views(self.scribble_left, self.scribble_right)
            
            # 기존 레이아웃에 추가
            # self.real_photo 대신 self.scribble_left 사용
```

## 참고사항

- PyQt5 기반으로 작성되었습니다
- 좌표 변환은 QGraphicsView의 내장 변환을 사용하므로 패딩/줌/스크롤이 자동으로 보정됩니다
- 브러시 크기는 상대 해상도에 비례하여 자동 조정됩니다

