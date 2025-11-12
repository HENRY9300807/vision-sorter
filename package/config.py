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
    )
    return _CFG

