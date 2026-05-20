"""ルーター（generate_route）のテスト。"""
from datetime import datetime

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
