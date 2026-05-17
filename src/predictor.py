"""待ち時間予測。"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.constants import POPULARITY_FACTOR, get_time_factor
from src.models import Attraction


def predict_wait(
    attraction: Attraction,
    current_wait: int,
    current_time: datetime,
    target_time: datetime,
    weather_mode: str = "normal",
) -> float:
    """target_time 時点の待ち時間を予測する。"""
    if target_time - current_time < timedelta(minutes=30):
        return float(current_wait)

    factor_now = get_time_factor(current_time.hour)
    factor_then = get_time_factor(target_time.hour)
    pop_factor = POPULARITY_FACTOR[attraction.popularity_tier]

    delta = (factor_then - factor_now) * pop_factor
    predicted = current_wait * (1 + delta)

    if weather_mode == "rain":
        predicted *= 0.7 if attraction.outdoor else 1.2

    return max(5.0, predicted)
