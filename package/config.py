# package/config.py

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    pixel_map_max_side: int = 256
    sphere_radius: int = 20
    capture_count: int = 100


def _int_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


_CFG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _CFG
    if _CFG is not None:
        return _CFG
    _CFG = AppConfig(
        pixel_map_max_side=_int_env("PIXEL_MAP_MAX_SIDE", 256),
        sphere_radius=_int_env("SPHERE_RADIUS", 20),
        capture_count=_int_env("CAPTURE_COUNT", 100),
    )
    return _CFG

