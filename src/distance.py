"""距離・移動時間の計算。"""
from __future__ import annotations

from datetime import datetime

from geopy.distance import geodesic

from src.constants import (
    MAIN_STREET_BLOCKING_PAIRS,
    MAIN_STREET_PENALTY_MIN,
    PARK_FACTOR_NORMAL,
    PARK_FACTOR_RAIN,
    WALKING_SPEED_M_PER_MIN,
)
from src.models import FixedBlock


def travel_time_min(
    loc_a: tuple[float, float],
    loc_b: tuple[float, float],
    current_time: datetime,
    fixed_blocks: list[FixedBlock],
    weather_mode: str = "normal",
    area_a: str | None = None,
    area_b: str | None = None,
) -> float:
    """二点間の移動時間（分）を返す。"""
    distance_m = geodesic(loc_a, loc_b).meters
    park_factor = PARK_FACTOR_RAIN if weather_mode == "rain" else PARK_FACTOR_NORMAL
    base = distance_m / WALKING_SPEED_M_PER_MIN * park_factor

    if area_a and area_b and _crosses_main_street(area_a, area_b):
        for block in fixed_blocks:
            if block.type == "parade" and not block.watch:
                if block.start <= current_time <= block.end:
                    base += MAIN_STREET_PENALTY_MIN
                    break

    return base


def _crosses_main_street(area_a: str, area_b: str) -> bool:
    return frozenset([area_a, area_b]) in MAIN_STREET_BLOCKING_PAIRS
