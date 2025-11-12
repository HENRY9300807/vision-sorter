# package/config.py

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    pixel_map_max_side: int = 256
    sphere_radius: int = 10  # 기존 값 유지 (환경 변수로 오버라이드 가능)
    capture_count: int = 100
    max_valid_saves: int = 100      # 유효 저장 상한
    cm_per_pixel: float = 0.01      # 1픽셀 당 cm (캘리브레이션 후 수정)
    defect_min_area_cm2: float = 0.05  # 트리거 면적 임계(cm^2)


def _int_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


_CFG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _CFG
    if _CFG is not None:
        return _CFG
    _CFG = AppConfig(
        pixel_map_max_side=_int_env("PIXEL_MAP_MAX_SIDE", 256),
        sphere_radius=_int_env("SPHERE_RADIUS", 10),
        capture_count=_int_env("CAPTURE_COUNT", 100),
        max_valid_saves=_int_env("MAX_VALID_SAVES", 100),
        cm_per_pixel=_float_env("CM_PER_PIXEL", 0.01),
        defect_min_area_cm2=_float_env("DEFECT_MIN_AREA_CM2", 0.05),
    )
    return _CFG

