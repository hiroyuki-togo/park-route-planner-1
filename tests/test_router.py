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


def test_rain_mode_deprioritizes_outdoor(sample_attractions, operating_snapshot):
    """雨天時、屋外（big_thunder）より屋内（pooh）が先に来やすくなる。"""
    # 同じ priority で並べる
    priorities = {"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5}

    normal = generate_route(
        snapshot=operating_snapshot, attractions=sample_attractions,
        constraints=make_constraints(), priorities=priorities, must_visits=set(),
        weather_mode="normal",
    )
    rain = generate_route(
        snapshot=operating_snapshot, attractions=sample_attractions,
        constraints=make_constraints(), priorities=priorities, must_visits=set(),
        weather_mode="rain",
    )

    normal_first = next(s.id for s in normal.steps if s.type == "attraction")
    rain_first = next(s.id for s in rain.steps if s.type == "attraction")

    # 雨天モード時に屋内（pooh）が優先される
    assert rain_first == "pooh"


def test_priority_zero_excluded_from_candidates(sample_attractions, operating_snapshot):
    """priority=0 のアトラクションは候補プールから除外される。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 0, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    # pooh は priority=0 で除外、big_thunder のみ訪問される
    assert "pooh" not in visited_ids
    assert "big_thunder" in visited_ids


def test_no_dpa_for_reserved_must(sample_attractions, operating_snapshot):
    """must-visit に予約必須アトラクションを入れたが DPA ブロックがない場合、警告が出る。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"beauty_and_beast"},
    )
    assert "beauty_and_beast" in result.unvisited_musts
    kinds = [w.kind for w in result.warnings]
    assert "no_dpa_for_reserved" in kinds


def test_visited_attractions_excluded(sample_attractions, operating_snapshot):
    """visited に渡したアトラクションは候補プールから除外される。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
        visited={"pooh"},
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    assert "pooh" not in visited_ids
    # big_thunder は残っているので訪問される
    assert "big_thunder" in visited_ids


def test_visited_clears_must_visit(sample_attractions, operating_snapshot):
    """must_visits と visited 両方に同じアトラクションがある場合、既消化扱いで unvisited_musts にも入らない。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"big_thunder"},
        visited={"big_thunder"},
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    assert "big_thunder" not in visited_ids
    assert "big_thunder" not in result.unvisited_musts


def test_past_fixed_block_skipped(sample_attractions, operating_snapshot):
    """start_time より完全に過去のブロックは消化対象にならない。"""
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 13, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="meal",
                start=datetime(2026, 5, 25, 10, 0),
                end=datetime(2026, 5, 25, 11, 0),
                label="朝食",
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
    assert meal_steps == []
    # かつ全 step の arrive が start_time 以降
    for s in result.steps:
        assert s.arrive >= constraints.start_time


def test_ongoing_block_arrive_clamped_to_current_time(sample_attractions, operating_snapshot):
    """start_time が block 内部にある場合、arrive は start_time 以降に丸められる。"""
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 13, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="meal",
                start=datetime(2026, 5, 25, 12, 0),
                end=datetime(2026, 5, 25, 13, 30),
                label="昼食",
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
    assert meal_steps[0].arrive == constraints.start_time  # 13:00 に丸められている
    assert meal_steps[0].ride_end == datetime(2026, 5, 25, 13, 30)


def test_route_starts_from_current_location(sample_attractions, operating_snapshot):
    """constraints.entrance をアトラクションの座標にすると、最初の travel_min が変わる。"""
    # entrance をエントランス起点にしたケース
    constraints_from_entrance = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[],
    )
    result_a = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints_from_entrance,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
    )
    # entrance を pooh の座標にしたケース（= 「今プーさん前にいる」状態）
    constraints_from_pooh = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6330, 139.8810),  # pooh の座標
        fixed_blocks=[],
    )
    result_b = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints_from_pooh,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
        visited={"pooh"},  # 既に乗ったので除外
    )
    # 最初の attraction step を比較
    first_a = next(s for s in result_a.steps if s.type == "attraction")
    first_b = next(s for s in result_b.steps if s.type == "attraction")
    # entrance 違いで最初の travel_min が異なる
    assert first_a.travel_min != first_b.travel_min
