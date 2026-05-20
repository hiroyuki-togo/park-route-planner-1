"""ルート生成（貪欲法 + スコアリング）。"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from pydantic import BaseModel

from src.constants import DPA_WAIT_MIN, EXP_VALUE
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
    attractions_by_id = {a.id: a for a in attractions}
    current_time = constraints.start_time
    current_location = constraints.entrance
    current_area: str | None = None
    visited: set[str] = set()
    must_remaining = set(must_visits)
    steps: list[RouteStep] = []
    warnings: list[Warning] = []
    blocks = sorted(constraints.fixed_blocks, key=lambda b: b.start)

    while current_time < constraints.close_time:
        # (A) 固定ブロック消化
        if blocks and blocks[0].start <= current_time:
            block = blocks.pop(0)
            step = _handle_fixed_block(block, current_time, current_location, attractions_by_id)
            if step is None:
                warnings.append(Warning(
                    kind="dpa_window_missed",
                    message=f"DPA 窓に間に合わず: {block.label}",
                    attraction_id=block.attraction_id,
                ))
                current_time = block.end
                continue
            steps.append(step)
            current_time = block.end
            if block.location:
                current_location = block.location
            if block.type == "dpa" and block.attraction_id:
                visited.add(block.attraction_id)
                must_remaining.discard(block.attraction_id)
            continue

        # (B) 通常候補
        candidates = _candidate_pool(attractions, snapshot, visited)
        if not candidates:
            # 候補なしでも固定ブロックが残っていれば、その時刻まで待機して消化
            if blocks:
                current_time = blocks[0].start
                continue
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

        # 次の固定ブロックまでに収まらない場合の分岐
        next_block_start = blocks[0].start if blocks else constraints.close_time
        time_until_block_min = (next_block_start - current_time).total_seconds() / 60
        if cost > time_until_block_min:
            if pending_must:
                # must は他の任意候補を後回しにしてでも入れたい
                if blocks:
                    # 固定ブロックを先に消化してから再挑戦
                    current_time = next_block_start
                    continue
                # 固定ブロックなし = 閉園までに物理的に入らない → この must を諦める
                # （ループ終了処理で time_conflict 警告を出す）
                must_remaining_size_before = len(must_remaining)
                must_remaining.discard(best.id)
                if len(must_remaining) == must_remaining_size_before:
                    # 何も外せなかった = ループが止まらないので break
                    break
                continue
            # 任意候補は fit_pool で絞って再評価
            fit_pool = []
            for a in candidates:
                s, t, w = _score(
                    a, current_time, current_location, current_area,
                    snapshot, priorities.get(a.id, 1),
                    constraints.fixed_blocks, weather_mode,
                )
                if t + w + a.experience_time_min <= time_until_block_min:
                    fit_pool.append(((s, t, w), a))
            if fit_pool:
                (best_score, travel, wait), best = max(fit_pool, key=lambda x: x[0][0])
                cost = travel + wait + best.experience_time_min
            else:
                # 収まる候補なし → 固定ブロック時刻まで current_time を進める
                current_time = next_block_start
                continue

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

    # 終了処理：未消化の DPA ブロックを警告に
    for block in blocks:
        if block.type == "dpa" and block.attraction_id:
            warnings.append(Warning(
                kind="dpa_window_missed",
                message=f"DPA 時間内に到達できず: {block.label}",
                attraction_id=block.attraction_id,
            ))

    # 終了処理：物理的に訪問できなかった must を警告に
    for must_id in sorted(must_remaining):
        warnings.append(Warning(
            kind="time_conflict",
            message=f"時間内に訪問できず: {must_id}",
            attraction_id=must_id,
        ))

    return RouteResult(
        steps=steps,
        unvisited_musts=sorted(must_remaining),
        warnings=warnings,
    )


def _handle_fixed_block(
    block: FixedBlock,
    current_time: datetime,
    current_location: tuple[float, float],
    attractions_by_id: dict[str, Attraction],
) -> RouteStep | None:
    """固定ブロックをルートステップに変換する。間に合わない DPA は None を返す。"""
    if block.type == "dpa":
        if not block.attraction_id or not block.location:
            return None
        attraction = attractions_by_id.get(block.attraction_id)
        if attraction is None:
            return None
        travel = travel_time_min(
            current_location, block.location,
            current_time, [], weather_mode="normal",
        )
        arrive = current_time + timedelta(minutes=travel)
        if arrive > block.end:
            return None
        actual_start = max(arrive, block.start)
        wait_min = DPA_WAIT_MIN
        ride_start = actual_start + timedelta(minutes=wait_min)
        ride_end = ride_start + timedelta(minutes=attraction.experience_time_min)
        return RouteStep(
            type="dpa", id=block.attraction_id,
            arrive=arrive, ride_start=ride_start, ride_end=ride_end,
            travel_min=travel, wait_min=wait_min, via="dpa",
            label=block.label,
        )
    if block.type == "meal":
        return RouteStep(
            type="meal", id=block.restaurant_id,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    if block.type == "show":
        return RouteStep(
            type="show", id=None,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    if block.type == "parade":
        return RouteStep(
            type="parade", id=None,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    return None
