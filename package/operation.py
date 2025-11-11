from pathlib import Path
from .config import get_config

# 설정 주입 (하드코딩 제거)
CFG = get_config()

# === 경로 ===
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PICTURE_DIR = ROOT_DIR / "picture"
COLOR_JSON_PATH = DATA_DIR / "color_defs.json"

# === UI 파라미터 ===
DRAW_POINT_RADIUS = 4
DRAW_POINT_LIMIT = 200
UI_UPDATE_INTERVAL = 1000   # 🔥 UI 갱신 주기 → 1초로 늘려서 버벅임 완화

# === 픽셀맵 파라미터 ===
# 분류맵 계산용 최대 해상도 축소 (성능 개선)
PIXEL_MAP_MAX_SIDE = CFG.pixel_map_max_side

# === Sphere 기본 반경 ===
SPHERE_RADIUS = CFG.sphere_radius

# === 캡처 관련 ===
CAPTURE_COUNT = CFG.capture_count
CAPTURE_TIMEOUT = 5000
JPEG_QUALITY = 90   
INTERVAL_SEC = 0.1

# === 카메라 관련 ===
CAMERA_BINNING_H = 2
CAMERA_BINNING_V = 2
CAMERA_DECIM_H = 2
CAMERA_DECIM_V = 2
