"""ルーター系テストの共通フィクスチャ。"""
from datetime import datetime

import pytest

from src.models import Attraction, WaitTimeEntry, WaitTimeSnapshot


@pytest.fixture
def sample_attractions():
    return [
        Attraction(
            id="pooh", name="プーさんのハニーハント", scrape_key="プーさん",
            area="ファンタジーランド", lat=35.6330, lng=139.8810,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            dpa_eligible=True, requires_reservation=False, outdoor=False,
            popularity_tier="S",
        ),
        Attraction(
            id="big_thunder", name="ビッグサンダー・マウンテン", scrape_key="ビッグサンダー",
            area="ウエスタンランド", lat=35.6322, lng=139.8780,
            experience_time_min=4, queue_walk_min=3, default_priority=4,
            dpa_eligible=False, requires_reservation=False, outdoor=True,
            popularity_tier="A",
        ),
        Attraction(
            id="beauty_and_beast", name="美女と野獣", scrape_key="美女と野獣",
            area="ファンタジーランド", lat=35.6336, lng=139.8808,
            experience_time_min=7, queue_walk_min=5, default_priority=5,
            dpa_eligible=True, requires_reservation=True, outdoor=False,
            popularity_tier="S",
        ),
    ]


@pytest.fixture
def operating_snapshot():
    return WaitTimeSnapshot(
        timestamp=datetime(2026, 5, 25, 9, 0),
        park="TDL",
        data=[
            WaitTimeEntry(name="プーさんのハニーハント", wait_min=30, status="operating"),
            WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=20, status="operating"),
            WaitTimeEntry(name="美女と野獣", wait_min=120, status="operating"),
        ],
    )


@pytest.fixture
def all_closed_snapshot():
    return WaitTimeSnapshot(
        timestamp=datetime(2026, 5, 25, 9, 0),
        park="TDL",
        data=[
            WaitTimeEntry(name="プーさんのハニーハント", wait_min=None, status="closed"),
            WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=None, status="closed"),
            WaitTimeEntry(name="美女と野獣", wait_min=None, status="closed"),
        ],
    )
