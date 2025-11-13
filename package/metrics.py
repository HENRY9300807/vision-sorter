# package/metrics.py
import numpy as np
import cv2


def largest_component_pixels(mask: np.ndarray, label_id: int) -> int:
    """지정 라벨의 가장 큰 연결성분 픽셀 수."""
    if mask is None:
        return 0
    bin_m = (mask == label_id).astype(np.uint8)
    if bin_m.max() == 0:
        return 0
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bin_m, connectivity=8)
    if n <= 1:
        return 0
    return int(stats[1:, cv2.CC_STAT_AREA].max())


def pixels_to_cm2(n_pixels: int, cm_per_pixel: float) -> float:
    """픽셀 수를 cm²로 변환."""
    return float(n_pixels) * (cm_per_pixel ** 2)

