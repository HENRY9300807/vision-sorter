# package/color_classifier.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
import cv2


# color_defs.json 형식: {"label": [[[R, G, B], radius], ...]}
# 현재 구조에 맞춰 RGB를 읽어서 LAB로 변환 후 분류
@dataclass(frozen=True)
class ColorDef:
    name: str
    lab: Tuple[float, float, float]
    radius: float


def bgr_to_lab(image_bgr: np.ndarray) -> np.ndarray:
    """
    OpenCV: BGR -> LAB 변환
    8-bit에선 a/b 보정이 들어가므로 동일한 규칙으로 비교
    """
    img = image_bgr
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)


def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """단일 RGB 튜플을 LAB로 변환"""
    # BGR 형식으로 변환 (OpenCV는 BGR 사용)
    b, g, r = rgb
    bgr_array = np.array([[[b, g, r]]], dtype=np.uint8)
    lab_array = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2LAB)
    lab = lab_array[0, 0]
    return (float(lab[0]), float(lab[1]), float(lab[2]))


def build_color_defs_from_json(data: Dict) -> List[ColorDef]:
    """
    현재 JSON 구조에서 ColorDef 리스트 생성
    JSON: {"label": [[[R, G, B], radius], ...]}
    """
    out = []
    for label, spheres in data.items():
        for center_rgb, radius in spheres:
            if not center_rgb or len(center_rgb) != 3:
                continue
            # RGB를 LAB로 변환
            lab = rgb_to_lab(tuple(center_rgb))
            out.append(ColorDef(name=label, lab=lab, radius=float(radius)))
    return out


def classify_lab_sphere(lab_img: np.ndarray, defs: List[ColorDef], default_radius: float = None) -> np.ndarray:
    """
    각 픽셀에 대해 가장 가까운 색상 구(sphere) 안에 들어오면 해당 인덱스를 매핑.
    반환: HxW int32 (라벨 인덱스, -1=미분류)
    
    Args:
        lab_img: LAB 색공간 이미지 (H, W, 3)
        defs: ColorDef 리스트
        default_radius: ColorDef에 radius가 없을 때 사용할 기본 반경
    """
    h, w, _ = lab_img.shape
    result = np.full((h, w), -1, dtype=np.int32)

    if not defs:
        return result

    # (H*W, 3)로 펴서 벡터화
    flat = lab_img.reshape(-1, 3).astype(np.float32)

    # 각 색상 정의에 대해 거리 계산
    min_dist = np.full((flat.shape[0],), np.inf, dtype=np.float32)
    min_idx = np.full((flat.shape[0],), -1, dtype=np.int32)

    for idx, c in enumerate(defs):
        c_lab = np.array(c.lab, dtype=np.float32)
        # ColorDef에 radius가 있으면 사용, 없으면 default_radius 사용
        radius = c.radius if hasattr(c, 'radius') and c.radius > 0 else (default_radius or 20.0)
        r2 = radius * radius
        
        d = flat - c_lab
        dist2 = (d * d).sum(axis=1)
        mask = dist2 <= r2
        # 더 가까운 색으로 갱신
        closer = mask & (dist2 < min_dist)
        min_idx[closer] = idx
        min_dist[closer] = dist2[closer]

    result[:, :] = min_idx.reshape(h, w)
    return result

