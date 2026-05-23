"""シミュレーションモード用の合成 WaitTimeSnapshot 生成。

来園日前のプランニング（叩き台作成）用に、実 API を叩かずに
理論値ベースの snapshot を作る。router は live モードと同じ I/F で受け取り、
内部で predictor.predict_wait() を呼んで時刻進行に応じた待ち時間を計算する。
"""
from __future__ import annotations

from datetime import date, datetime, time

from src.constants import (
    OPENING_BASE_WAIT_BY_TIER,
    TIME_FACTOR_AVG_EFFECTIVE,
    TIME_FACTOR_FLOOR,
    get_time_factor,
)
from src.models import Attraction, WaitTimeEntry, WaitTimeSnapshot


def build_opening_snapshot(
    attractions: list[Attraction],
    target_date: date,
) -> WaitTimeSnapshot:
    """target_date の 9:00 開園想定の合成 snapshot を返す。

    各エントリの wait_min は Queue-Times stats の全期間平均（avg_wait_min）を
    優先し、未収録のものは tier ベースの OPENING_BASE_WAIT_BY_TIER でフォール
    バックする。
    """
    ts = datetime.combine(target_date, time(9, 0))
    entries = [
        WaitTimeEntry(
            name=a.name,
            wait_min=(
                a.avg_wait_min
                if a.avg_wait_min is not None
                else OPENING_BASE_WAIT_BY_TIER[a.popularity_tier]
            ),
            status="operating",
            queue_times_id=a.queue_times_id,
        )
        for a in attractions
    ]
    return WaitTimeSnapshot(timestamp=ts, park="TDL", data=entries)


def build_snapshot_at(
    attractions: list[Attraction],
    target_datetime: datetime,
) -> WaitTimeSnapshot:
    """target_datetime 時点の合成 snapshot を返す。

    各エントリの wait_min は Queue-Times stats の全期間平均 (avg_wait_min) に
    時刻補正 (effective_factor / TIME_FACTOR_AVG_EFFECTIVE) を掛けた値。
    avg_wait_min が null の場合は tier ベースの OPENING_BASE_WAIT_BY_TIER に
    同じ時刻補正を適用。effective_factor は get_time_factor(target_datetime.hour)
    を TIME_FACTOR_FLOOR で下限保護した値。
    """
    effective_factor = max(TIME_FACTOR_FLOOR, get_time_factor(target_datetime.hour))
    multiplier = effective_factor / TIME_FACTOR_AVG_EFFECTIVE
    entries = [
        WaitTimeEntry(
            name=a.name,
            wait_min=round(
                (a.avg_wait_min if a.avg_wait_min is not None
                 else OPENING_BASE_WAIT_BY_TIER[a.popularity_tier])
                * multiplier
            ),
            status="operating",
            queue_times_id=a.queue_times_id,
        )
        for a in attractions
    ]
    return WaitTimeSnapshot(timestamp=target_datetime, park="TDL", data=entries)
