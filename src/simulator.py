"""シミュレーションモード用の合成 WaitTimeSnapshot 生成。

来園日前のプランニング（叩き台作成）用に、実 API を叩かずに
理論値ベースの snapshot を作る。router は live モードと同じ I/F で受け取り、
内部で predictor.predict_wait() を呼んで時刻進行に応じた待ち時間を計算する。
"""
from __future__ import annotations

from datetime import date, datetime, time

from src.constants import OPENING_BASE_WAIT_BY_TIER
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
