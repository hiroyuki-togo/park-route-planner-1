"""シミュレーションモード（合成 snapshot 生成）のテスト。"""
from datetime import date, datetime, time

from src.constants import OPENING_BASE_WAIT_BY_TIER
from src.models import Attraction, WaitTimeSnapshot
from src.router import RouteConstraints, generate_route
from src.simulator import build_snapshot_at


def test_snapshot_at_basic(sample_attractions):
    """9:00 を渡すと、avg_wait_min null のアトラクションは tier base × 0.8244 で計算される。"""
    snap = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))

    assert isinstance(snap, WaitTimeSnapshot)
    assert all(e.status == "operating" for e in snap.data)
    # multiplier = 0.9 / (13.1/12) = 0.8244
    expected = {
        "S": round(OPENING_BASE_WAIT_BY_TIER["S"] * 0.8244),  # 16
        "A": round(OPENING_BASE_WAIT_BY_TIER["A"] * 0.8244),  # 12
        "B": round(OPENING_BASE_WAIT_BY_TIER["B"] * 0.8244),  # 8
        "C": round(OPENING_BASE_WAIT_BY_TIER["C"] * 0.8244),  # 4
    }
    for entry, attr in zip(snap.data, sample_attractions):
        assert entry.name == attr.name
        assert entry.wait_min == expected[attr.popularity_tier]


def test_snapshot_at_timestamp_preserves_input(sample_attractions):
    """snapshot.timestamp が引数の datetime そのまま保持される。"""
    target_dt = datetime(2026, 5, 25, 11, 30)
    snap = build_snapshot_at(sample_attractions, target_dt)

    assert snap.timestamp == target_dt
    assert snap.park == "TDL"


def test_snapshot_at_count(sample_attractions):
    snap = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))
    assert len(snap.data) == len(sample_attractions)


def test_snapshot_at_determinism(sample_attractions):
    """同じ引数なら同じ結果。"""
    target_dt = datetime(2026, 5, 25, 9, 0)
    snap_a = build_snapshot_at(sample_attractions, target_dt)
    snap_b = build_snapshot_at(sample_attractions, target_dt)
    assert snap_a == snap_b


def test_snapshot_at_empty_attractions():
    target_dt = datetime(2026, 5, 25, 9, 0)
    snap = build_snapshot_at([], target_dt)
    assert isinstance(snap, WaitTimeSnapshot)
    assert snap.data == []
    assert snap.timestamp == target_dt


def test_snapshot_at_uses_avg_wait_when_present():
    """avg_wait_min が設定されていれば、tier フォールバックでなく avg × multiplier を使う。"""
    attractions = [
        Attraction(
            id="with_avg", name="With Avg", scrape_key="W",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="S",
            queue_times_id=9999, avg_wait_min=42,
        ),
        Attraction(
            id="no_avg", name="No Avg", scrape_key="N",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="C",
        ),
    ]
    snap = build_snapshot_at(attractions, datetime(2026, 5, 25, 9, 0))
    by_name = {e.name: e for e in snap.data}
    # 9:00 multiplier = 0.9 / (13.1/12) ≈ 0.8244
    assert by_name["With Avg"].wait_min == round(42 * (0.9 / (13.1 / 12)))  # = 35
    assert by_name["No Avg"].wait_min == round(OPENING_BASE_WAIT_BY_TIER["C"] * (0.9 / (13.1 / 12)))  # = 4


def test_snapshot_at_morning_vs_peak(sample_attractions):
    """9:00（朝係数 0.7→下限 0.9）と 11:00（ピーク 1.3）で同じアトラクションの wait_min が異なる。"""
    morning = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))
    peak = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 11, 0))

    # avg=None のアトラクションでも、tier base × multiplier の差が出るはず
    by_name_morning = {e.name: e.wait_min for e in morning.data}
    by_name_peak = {e.name: e.wait_min for e in peak.data}
    for name in by_name_morning:
        # 11:00 は 9:00 の (1.3/0.9) ≈ 1.44 倍
        assert by_name_peak[name] > by_name_morning[name]


def test_snapshot_at_floor_protection(sample_attractions):
    """営業時間外（早朝 / 閉園後）でも factor が 0.9 下限を割らない。"""
    # 03:00 と 22:00 — どちらも factor が 0.7 だが下限 0.9 で持ち上がる
    early = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 3, 0))
    late = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 22, 0))

    # 22:00 と 03:00 は同じ multiplier (0.9/(13.1/12)) になるはず
    early_by_name = {e.name: e.wait_min for e in early.data}
    late_by_name = {e.name: e.wait_min for e in late.data}
    for name in early_by_name:
        assert early_by_name[name] == late_by_name[name]

    # 値が tier base × 0.8244 になっていることを 1 件で確認
    pooh = next(e for e in early.data if e.name == "プーさんのハニーハント")
    # S 級 tier base = 20、0.9/(13.1/12) ≈ 0.8244 → round = 16
    assert pooh.wait_min == round(OPENING_BASE_WAIT_BY_TIER["S"] * (0.9 / (13.1 / 12)))


def test_snapshot_at_avg_null_uses_tier_base_with_multiplier():
    """avg_wait_min=None のアトラクションは tier base × multiplier で計算される（ただ tier base 直接ではない）。"""
    attractions = [
        Attraction(
            id="s_no_avg", name="S No Avg", scrape_key="S",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="S",
        ),
    ]
    # 11:00（ピーク 1.3）でテスト
    snap = build_snapshot_at(attractions, datetime(2026, 5, 25, 11, 0))
    # multiplier = 1.3 / (13.1/12) ≈ 1.1908
    # 20 × 1.1908 = 23.82 → round = 24
    assert snap.data[0].wait_min == round(OPENING_BASE_WAIT_BY_TIER["S"] * (1.3 / (13.1 / 12)))


def test_simulate_then_route(sample_attractions):
    """合成 snapshot を router に流して、開園想定で全体ルートが返ることを確認。"""
    target_date = date(2026, 5, 25)
    snap = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))
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
