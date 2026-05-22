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
    """target_date の 9:00 開園想定の合成 snapshot を返す。"""
    ts = datetime.combine(target_date, time(9, 0))
    entries = [
        WaitTimeEntry(
            name=a.name,
            wait_min=OPENING_BASE_WAIT_BY_TIER[a.popularity_tier],
            status="operating",
        )
        for a in attractions
    ]
    return WaitTimeSnapshot(timestamp=ts, park="TDL", data=entries)
