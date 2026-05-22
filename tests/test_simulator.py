"""シミュレーションモード（合成 snapshot 生成）のテスト。"""
from datetime import date, datetime, time

from src.constants import OPENING_BASE_WAIT_BY_TIER
from src.models import Attraction, WaitTimeSnapshot
from src.router import RouteConstraints, generate_route
from src.simulator import build_opening_snapshot


def test_opening_snapshot_basic(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))

    assert isinstance(snap, WaitTimeSnapshot)
    assert all(e.status == "operating" for e in snap.data)
    for entry, attr in zip(snap.data, sample_attractions):
        assert entry.name == attr.name
        assert entry.wait_min == OPENING_BASE_WAIT_BY_TIER[attr.popularity_tier]


def test_opening_snapshot_timestamp(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))

    assert snap.timestamp.date() == date(2026, 5, 25)
    assert snap.timestamp.time() == time(9, 0)
    assert snap.park == "TDL"


def test_opening_snapshot_count(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    assert len(snap.data) == len(sample_attractions)


def test_opening_snapshot_determinism(sample_attractions):
    snap_a = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    snap_b = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    assert snap_a == snap_b


def test_opening_snapshot_empty_attractions():
    snap = build_opening_snapshot([], date(2026, 5, 25))
    assert isinstance(snap, WaitTimeSnapshot)
    assert snap.data == []
    assert snap.timestamp == datetime(2026, 5, 25, 9, 0)


def test_opening_snapshot_uses_avg_wait_when_present():
    """avg_wait_min が設定されているアトラクションは tier フォールバックではなく avg を使う。"""
    attractions = [
        Attraction(
            id="with_avg", name="With Avg", scrape_key="W",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="S",  # 基準 20 だが avg 42 が優先されるはず
            queue_times_id=9999, avg_wait_min=42,
        ),
        Attraction(
            id="no_avg", name="No Avg", scrape_key="N",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="C",  # avg なし → 基準 5 がフォールバック
        ),
    ]
    snap = build_opening_snapshot(attractions, date(2026, 5, 25))
    by_name = {e.name: e for e in snap.data}
    assert by_name["With Avg"].wait_min == 42
    assert by_name["No Avg"].wait_min == OPENING_BASE_WAIT_BY_TIER["C"]


def test_simulate_then_route(sample_attractions):
    """合成 snapshot を router に流して、開園想定で全体ルートが返ることを確認。"""
    target_date = date(2026, 5, 25)
    snap = build_opening_snapshot(sample_attractions, target_date)
    constraints = RouteConstraints(
        start_time=datetime.combine(target_date, time(9, 0)),
        close_time=datetime.combine(target_date, time(21, 0)),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[],
    )
    result = generate_route(
        snapshot=snap,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    visited = [s.id for s in result.steps if s.type == "attraction"]
    # operating 扱いなので候補プールから除外されない。pooh と big_thunder は訪問できる。
    assert "pooh" in visited
    assert "big_thunder" in visited
