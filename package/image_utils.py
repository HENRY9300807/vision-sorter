# package/image_utils.py
import cv2
import numpy as np
from package.color_utils import COLOR_DEFS  # 전역 정의 사용
from package.operation import PIXEL_MAP_MAX_SIDE  # 다운스케일 최대 크기


def to_pixmap(img_bgr, QtGui):
    """BGR numpy → QPixmap"""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = img_rgb.shape
    qimg = QtGui.QImage(img_rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg)


def draw_points(img, points, color=(0, 0, 255), radius=5):
    """점(드래그 자취) 표시"""
    overlay = img.copy()
    for (x, y) in points:
        cv2.circle(overlay, (x, y), radius, color, -1)
    return overlay


def highlight_rgb(img_bgr, rgb_set):
    """선택한 RGB 값과 같은 픽셀을 강조(초록)"""
    h, w = img_bgr.shape[:2]
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    mask = np.isin(
        img_rgb.reshape(-1, 3).view([('', img_rgb.dtype)] * 3),
        np.array(list(rgb_set)).view([('', np.uint8)] * 3)
    )
    mask = mask.reshape(h, w)

    overlay = img_rgb.copy()
    overlay[mask] = (0, 255, 0)
    return cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)


# ======================
# ⚡ 벡터화된 픽셀 분류 + 다운스케일
# ======================
def make_pixel_map(img_bgr):
    """
    이미지 전체를 타일/배치로 나눠 안전하게 벡터화 분류.
    - unknown: 분홍 (255, 0, 255)
    - product: 초록 (0, 255, 0)
    - background: 파랑 (0, 0, 255)
    - defect: 검정 (0, 0, 0)

    성능 최적화:
      * 긴 변을 PIXEL_MAP_MAX_SIDE 로 다운스케일 (INTER_AREA)
      * 분류 계산 후 NEAREST 업스케일로 원해상도 복원
    """
    # 타일/배치 파라미터
    TILE_H, TILE_W = 256, 256
    SPHERE_CHUNK = 256

    h, w = img_bgr.shape[:2]
    img_rgb_full = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # --- (A) 다운스케일 ---
    scale = 1.0
    img_rgb = img_rgb_full
    if PIXEL_MAP_MAX_SIDE and max(h, w) > PIXEL_MAP_MAX_SIDE:
        scale = PIXEL_MAP_MAX_SIDE / float(max(h, w))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img_rgb = cv2.resize(img_rgb_full, (new_w, new_h), interpolation=cv2.INTER_AREA)

    img_rgb = img_rgb.astype(np.int16)
    hh, ww = img_rgb.shape[:2]

    # 결과 초기화: 분홍(unknown)
    result = np.full((hh, ww, 3), (255, 0, 255), dtype=np.uint8)
    assigned = np.zeros((hh, ww), dtype=bool)

    # 라벨 색상 및 우선순위
    label_colors = {
        "product":    np.array([0, 255, 0], dtype=np.uint8),
        "background": np.array([0, 0, 255], dtype=np.uint8),
        "defect":     np.array([0, 0, 0], dtype=np.uint8),
    }
    # 우선순위: product > defect > background
    label_order = ["product", "defect", "background"]

    # 라벨별 스피어 준비
    prepped = {}
    for label in label_order:
        spheres = COLOR_DEFS.get(label, [])
        if not spheres:
            continue
        centers = np.array([c for (c, r) in spheres], dtype=np.int16)     # (M,3)
        radii2  = (np.array([r for (c, r) in spheres], dtype=np.int32) ** 2)  # (M,)
        prepped[label] = (centers, radii2)

    # 스피어가 전혀 없으면 바로 리턴
    if not prepped:
        if scale != 1.0:
            return cv2.resize(result, (w, h), interpolation=cv2.INTER_NEAREST)
        return result

    # --- 타일 단위 처리 ---
    for y0 in range(0, hh, TILE_H):
        y1 = min(y0 + TILE_H, hh)
        for x0 in range(0, ww, TILE_W):
            x1 = min(x0 + TILE_W, ww)

            remain_mask_tile = ~assigned[y0:y1, x0:x1]
            if not np.any(remain_mask_tile):
                continue

            tile = img_rgb[y0:y1, x0:x1]
            flat_tile = tile.reshape(-1, 3)
            flat_remain = remain_mask_tile.reshape(-1)
            idx_map = np.nonzero(flat_remain)[0]
            if idx_map.size == 0:
                continue

            P = flat_tile[idx_map]     # (Kr, 3)
            Kr = P.shape[0]

            tile_assign = np.zeros(Kr, dtype=bool)
            tile_color  = np.full((Kr, 3), (255, 0, 255), dtype=np.uint8)

            for label in label_order:
                if label not in prepped:
                    continue
                centers, radii2 = prepped[label]
                if centers.shape[0] == 0:
                    continue

                hit_any = np.zeros(Kr, dtype=bool)

                # 스피어를 배치로 쪼개서 계산 (메모리 절약)
                for s0 in range(0, centers.shape[0], SPHERE_CHUNK):
                    s1 = min(s0 + SPHERE_CHUNK, centers.shape[0])
                    C = centers[s0:s1]              # (Mc,3)
                    R2 = radii2[s0:s1]              # (Mc,)

                    # (Kr,3) - (Mc,3) → (Kr,Mc,3)
                    diffs = P[:, None, :] - C[None, :, :]
                    # 제곱거리: Σ (P-C)^2
                    dist2 = np.einsum('ijk,ijk->ij', diffs, diffs, dtype=np.int32)
                    hit_any |= np.any(dist2 <= R2[None, :], axis=1)

                    # del diffs, dist2  # ← 굳이 지울 필요 없음(예외 방지 차 제거)

                newly = hit_any & (~tile_assign)
                if np.any(newly):
                    tile_color[newly] = label_colors[label]
                    tile_assign[newly] = True

                # 타일 내 모든 픽셀 배정 완료되면 조기 종료
                if np.all(tile_assign):
                    break

            # 타일 결과 반영
            flat_out = result[y0:y1, x0:x1].reshape(-1, 3)
            flat_out[idx_map] = tile_color
            assigned[y0:y1, x0:x1] |= remain_mask_tile

    # --- (B) 업스케일 ---
    if scale != 1.0:
        # 최근접 업스케일로 경계 보존
        return cv2.resize(result, (w, h), interpolation=cv2.INTER_NEAREST)
    return result

