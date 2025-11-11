import json
from pathlib import Path
from package.operation import COLOR_JSON_PATH, SPHERE_RADIUS

# =========================
# 전역 저장소 & 파일 경로
# =========================
COLOR_DEFS = {
    "background": [],
    "product": [],
    "defect": [],
}
SAVE_FILE = COLOR_JSON_PATH


# =========================
# 유틸
# =========================
def _to_rgb_tuple(rgb):
    """(r,g,b)을 파이썬 int로 강제 캐스팅해 안전화"""
    r, g, b = rgb
    return (int(r), int(g), int(b))

def _is_iter_of_rgb(x):
    """[(r,g,b), ...] 형태인지 판별"""
    try:
        it = iter(x)
        first = next(it)
        return isinstance(first, (tuple, list)) and len(first) == 3
    except Exception:
        return False


# =========================
# 기능 함수
# =========================
def get_rgb(img, x, y):
    """이미지에서 (x,y) 픽셀의 RGB 추출 (BGR -> RGB)"""
    h, w = img.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        b, g, r = img[int(y), int(x)]
        return (int(r), int(g), int(b))
    return None


def add_color_def(label, center_rgb, radius=SPHERE_RADIUS, defs=None):
    """
    새로운 색상 정의 추가 (구 형태).
    - center_rgb: (r,g,b) 또는 {(r,g,b), ...} / [(r,g,b), ...]
    """
    target = COLOR_DEFS if defs is None else defs
    if label not in target:
        target[label] = []

    rad = int(radius)

    # 여러 RGB가 들어온 경우
    if _is_iter_of_rgb(center_rgb):
        for rgb in center_rgb:
            target[label].append((_to_rgb_tuple(rgb), rad))
    # set 같은 컨테이너도 처리
    elif isinstance(center_rgb, (set, list, tuple)) and center_rgb and isinstance(next(iter(center_rgb)), (int,)):
        # 실수로 flat한 [r,g,b]가 들어오는 경우 보정
        if len(center_rgb) == 3:
            target[label].append((_to_rgb_tuple(tuple(center_rgb)), rad))
        else:
            # 예외적인 케이스는 무시
            pass
    else:
        # 단일 RGB
        target[label].append((_to_rgb_tuple(center_rgb), rad))


def classify_rgb(rgb, defs=None):
    """
    RGB값이 어떤 색상 정의 구 안에 포함되는지 분류.
    - 오버플로 방지를 위해 모두 int로 변환 후 제곱거리로 비교
    """
    target = COLOR_DEFS if defs is None else defs
    r, g, b = _to_rgb_tuple(rgb)

    for label, spheres in target.items():
        for center, radius in spheres:
            cr, cg, cb = _to_rgb_tuple(center)
            rad2 = int(radius) * int(radius)

            dr = r - cr
            dg = g - cg
            db = b - cb

            if (dr * dr + dg * dg + db * db) <= rad2:
                return label
    return "unknown"


# =========================
# JSON 저장/로드/초기화
# =========================
def save_defs(filepath=SAVE_FILE):
    """현재 COLOR_DEFS를 JSON 파일로 저장"""
    serializable = {
        k: [[list(_to_rgb_tuple(center)), int(radius)] for center, radius in v]
        for k, v in COLOR_DEFS.items()
    }
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"색상 정의 저장됨 → {filepath}")


def load_defs(filepath=SAVE_FILE):
    """JSON 파일에서 COLOR_DEFS 불러오기 (타입 정규화 포함)"""
    if not Path(filepath).exists():
        print("⚠️ 저장된 색상 정의 파일 없음")
        return
    try:
        text = Path(filepath).read_text(encoding="utf-8").strip()
        if not text:
            print("⚠️ 색상 정의 파일이 비어 있음")
            return
        data = json.loads(text)

        # in-place 업데이트 (전역 객체 참조 유지)
        COLOR_DEFS.clear()
        for k in ("background", "product", "defect"):
            COLOR_DEFS[k] = []

        for k, v in data.items():
            fixed_list = []
            for center, radius in v:
                fixed_list.append((_to_rgb_tuple(center), int(radius)))
            COLOR_DEFS[k] = fixed_list

        print(f"색상 정의 불러옴 ← {filepath}")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON 파싱 실패: {e}")


def clear_defs(filepath=SAVE_FILE):
    """JSON 파일과 메모리의 COLOR_DEFS를 초기화"""
    COLOR_DEFS.clear()
    COLOR_DEFS.update({
        "background": [],
        "product": [],
        "defect": [],
    })
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(COLOR_DEFS, f, indent=2, ensure_ascii=False)
    print(f"🚮 색상 정의 초기화 완료 → {filepath}")
