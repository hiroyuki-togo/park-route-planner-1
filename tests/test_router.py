"""ルーター（generate_route）のテスト。"""
from datetime import datetime

from src.models import FixedBlock
from src.router import RouteConstraints, generate_route


def make_constraints():
    return RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[],
    )


def test_all_closed_returns_empty(sample_attractions, all_closed_snapshot):
    result = generate_route(
        snapshot=all_closed_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    assert result.steps == []


def test_basic_route_visits_high_priority(sample_attractions, operating_snapshot):
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    # 美女と野獣は requires_reservation=True で DPA なしなので除外される
    assert "beauty_and_beast" not in visited_ids
    # 残り 2 件が訪問される
    assert "pooh" in visited_ids
    assert "big_thunder" in visited_ids


def test_must_visit_consumed_first(sample_attractions, operating_snapshot):
    """must_visits に big_thunder が入っていれば、priority が同じでも先に訪問される。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"big_thunder"},
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    # big_thunder が最初
    assert visited_ids[0] == "big_thunder"


def test_unvisited_must_returned(sample_attractions, operating_snapshot):
    """closed のアトラクションを must にした場合、unvisited_musts に残る。"""
    snapshot_with_closed = operating_snapshot.model_copy()
    snapshot_with_closed.data[1].status = "closed"  # big_thunder closed

    result = generate_route(
        snapshot=snapshot_with_closed,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"big_thunder"},
    )
    assert "big_thunder" in result.unvisited_musts


def test_dpa_block_visits_reserved_attraction(sample_attractions, operating_snapshot):
    """DPA ブロックが指定時間に消化され、requires_reservation のアトラクションが訪問される。"""
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="dpa",
                start=datetime(2026, 5, 25, 10, 30),
                end=datetime(2026, 5, 25, 11, 30),
                label="DPA: 美女と野獣",
                attraction_id="beauty_and_beast",
                location=(35.6336, 139.8808),
            ),
        ],
    )
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"beauty_and_beast"},
    )
    dpa_steps = [s for s in result.steps if s.type == "dpa"]
    assert len(dpa_steps) == 1
    assert dpa_steps[0].id == "beauty_and_beast"
    assert dpa_steps[0].via == "dpa"
    assert dpa_steps[0].wait_min == 15
    assert "beauty_and_beast" not in result.unvisited_musts


def test_meal_block_anchors_location(sample_attractions, operating_snapshot):
    """食事ブロックに location があれば、ブロック終了後の現在地が更新される。

    fixture の訪問可能アトラクションが 2 件のみのため、ブロックを朝早めに置いて
    食事後にも訪問が残る構成にしている（プラン原案の 12:00 開始から変更）。
    """
    meal_location = (35.6325, 139.8800)
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="meal",
                start=datetime(2026, 5, 25, 9, 30),
                end=datetime(2026, 5, 25, 10, 30),
                label="軽食",
                location=meal_location,
            ),
        ],
    )
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
    )
    meal_steps = [s for s in result.steps if s.type == "meal"]
    assert len(meal_steps) == 1
    # 食事後のアトラクション訪問が存在する（=ルートが継続している）
    after_meal = [s for s in result.steps if s.type == "attraction" and s.arrive > meal_steps[0].ride_end]
    assert len(after_meal) > 0
