"""ルート生成（貪欲法 + スコアリング）。"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from pydantic import BaseModel

from src.constants import EXP_VALUE
from src.distance import travel_time_min
from src.models import (
    Attraction,
    FixedBlock,
    RouteResult,
    RouteStep,
    WaitTimeSnapshot,
    Warning,
)
from src.predictor import predict_wait
from src.scraper import match_attraction_by_scrape_key


class RouteConstraints(BaseModel):
    start_time: datetime
    close_time: datetime
    entrance: tuple[float, float]
    fixed_blocks: list[FixedBlock]


def _is_operating(attraction: Attraction, snapshot: WaitTimeSnapshot) -> bool:
    entry = match_attraction_by_scrape_key(snapshot.data, attraction.scrape_key)
    return entry is not None and entry.status == "operating"


def _current_wait(attraction: Attraction, snapshot: WaitTimeSnapshot) -> int:
    entry = match_attraction_by_scrape_key(snapshot.data, attraction.scrape_key)
    return entry.wait_min if entry and entry.wait_min is not None else 0


def _candidate_pool(
    attractions: Iterable[Attraction],
    snapshot: WaitTimeSnapshot,
    visited: set[str],
) -> list[Attraction]:
    return [
        a for a in attractions
        if a.id not in visited
        and not a.requires_reservation
        and _is_operating(a, snapshot)
    ]


def _score(
    attraction: Attraction,
    current_time: datetime,
    current_location: tuple[float, float],
    current_area: str | None,
    snapshot: WaitTimeSnapshot,
    priority: int,
    fixed_blocks: list[FixedBlock],
    weather_mode: str,
) -> tuple[float, float, float]:
    """スコア・移動時間・予測待ちを返す。"""
    travel = travel_time_min(
        current_location, (attraction.lat, attraction.lng),
        current_time, fixed_blocks, weather_mode,
        area_a=current_area, area_b=attraction.area,
    )
    arrive = current_time + timedelta(minutes=travel)
    wait = predict_wait(
        attraction, _current_wait(attraction, snapshot),
        snapshot.timestamp, arrive, weather_mode,
    )
    cost = travel + wait + attraction.experience_time_min
    weather_value_factor = 0.7 if (weather_mode == "rain" and attraction.outdoor) else 1.0
    score = (priority * EXP_VALUE[attraction.popularity_tier] * weather_value_factor) / max(cost, 1)
    return score, travel, wait


def generate_route(
    snapshot: WaitTimeSnapshot,
    attractions: list[Attraction],
    constraints: RouteConstraints,
    priorities: dict[str, int],
    must_visits: set[str],
    weather_mode: str = "normal",
) -> RouteResult:
    """ルートを生成する。"""
    current_time = constraints.start_time
    current_location = constraints.entrance
    current_area: str | None = None
    visited: set[str] = set()
    must_remaining = set(must_visits)
    steps: list[RouteStep] = []
    warnings: list[Warning] = []

    while current_time < constraints.close_time:
        candidates = _candidate_pool(attractions, snapshot, visited)
        if not candidates:
            break

        pending_must = [c for c in candidates if c.id in must_remaining]
        pool = pending_must if pending_must else candidates

        scored = [
            (_score(
                a, current_time, current_location, current_area,
                snapshot, priorities.get(a.id, 1),
                constraints.fixed_blocks, weather_mode,
            ), a)
            for a in pool
        ]
        (best_score, travel, wait), best = max(scored, key=lambda x: x[0][0])
        cost = travel + wait + best.experience_time_min

        if current_time + timedelta(minutes=cost) > constraints.close_time:
            break

        arrive = current_time + timedelta(minutes=travel)
        ride_start = arrive + timedelta(minutes=wait)
        ride_end = ride_start + timedelta(minutes=best.experience_time_min)

        steps.append(RouteStep(
            type="attraction", id=best.id,
            arrive=arrive, ride_start=ride_start, ride_end=ride_end,
            travel_min=travel, wait_min=wait, via="standby",
            label=best.name,
        ))
        current_time = ride_end
        current_location = (best.lat, best.lng)
        current_area = best.area
        visited.add(best.id)
        must_remaining.discard(best.id)

    return RouteResult(
        steps=steps,
        unvisited_musts=sorted(must_remaining),
        warnings=warnings,
    )
