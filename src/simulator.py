"""シミュレーションモード用の合成 WaitTimeSnapshot 生成。

来園日前のプランニング（叩き台作成）用に、実 API を叩かずに
理論値ベースの snapshot を作る。任意時刻スタートに対応し、合成 snapshot 内の
wait_min は時刻補正（下限 0.9 つき）された値を持つ。
"""
from __future__ import annotations

from datetime import datetime

from src.constants import (
    OPENING_BASE_WAIT_BY_TIER,
    TIME_FACTOR_AVG_EFFECTIVE,
    TIME_FACTOR_FLOOR,
    get_time_factor,
)
from src.models import Attraction, WaitTimeEntry, WaitTimeSnapshot


def is_snapshot_off_hours(snapshot: WaitTimeSnapshot) -> bool:
    """snapshot.timestamp が営業時間外（< 9 時 or >= 21 時）かを判定。

    Queue-Times.com は閉園後 / 開園前に全アトラクションの status を 'closed'
    として返すため、その snapshot を当日モードのルート生成に使うと、router の
    _is_operating() が全件を「運営中じゃない」と判定して候補プールが空になる。
    結果として予約済み枠と食事ブロックだけのスカスカルートが生成される構造的バグ。

    本判定で True を返す場合、呼び出し側は build_snapshot_at() で合成 snapshot に
    差し替えることを推奨（実 wait_min が信用できないため）。
    """
    hour = snapshot.timestamp.hour
    return hour < 9 or hour >= 21


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
