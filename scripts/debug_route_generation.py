"""東郷さんの 2026-05-23 セッションで再現したルート生成バグの調査スクリプト。

設定:
- 当日モード、現在時刻 10:00
- 予約済み枠: プーさん (priority, 10:30-11:30) + 美女と野獣 (DPA, 14:00-14:30)
- 食事: 13:00-14:00 北斎
- 必ず乗る: 美女と野獣 / プーさん
- 多数のアトラクションが priority>0 で候補に入っているはずなのに、ルートは 3 ステップ
  しか生成されない（プーさん → 食事 → 美女と野獣）。

debug 後、本スクリプトは削除可。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.models import Attraction, FixedBlock, WaitTimeEntry, WaitTimeSnapshot
from src.router import RouteConstraints, generate_route


def load_attractions() -> list[Attraction]:
    data = json.loads(Path("data/attractions.json").read_text())
    return [Attraction(**a) for a in data["attractions"]]


def make_snapshot(attractions: list[Attraction], current_time: datetime) -> WaitTimeSnapshot:
    """全アトラクションを operating、wait_min は avg を current として使う簡易 snapshot。"""
    entries = []
    for a in attractions:
        if a.queue_times_id is None:
            continue
        entries.append(WaitTimeEntry(
            queue_times_id=a.queue_times_id,
            name=a.name,
            wait_min=a.avg_wait_min or 20,
            status="operating",
        ))
    return WaitTimeSnapshot(park="TDL", timestamp=current_time, data=entries)


def main() -> None:
    attractions = load_attractions()
    entrance = (35.6329, 139.8804)
    today = datetime(2026, 5, 25, 0, 0, 0)
    current_time = today.replace(hour=10, minute=0)
    close_time = today.replace(hour=21, minute=0)

    pooh = next(a for a in attractions if a.id == "pooh")
    beauty = next(a for a in attractions if a.id == "beauty_and_beast")

    fixed_blocks = [
        FixedBlock(
            type="dpa",
            attraction_id="pooh",
            start=today.replace(hour=10, minute=30),
            end=today.replace(hour=11, minute=30),
            location=(pooh.lat, pooh.lng),
            label=f"DPA: {pooh.name}",
        ),
        FixedBlock(
            type="meal",
            restaurant_id="hokusai",
            start=today.replace(hour=13, minute=0),
            end=today.replace(hour=14, minute=0),
            location=None,
            label="れすとらん北齋",
        ),
        FixedBlock(
            type="dpa",
            attraction_id="beauty_and_beast",
            start=today.replace(hour=14, minute=0),
            end=today.replace(hour=14, minute=30),
            location=(beauty.lat, beauty.lng),
            label=f"DPA: {beauty.name}",
        ),
    ]

    # 東郷さんのスクショから読み取った priority 設定
    priorities = {
        "monsters_inc": 1,
        "minnie_style": 3,
        "roger_rabbit": 3,
        "its_a_small_world": 5,
        "peter_pan": 5,
        "pooh": 5,
        "haunted_mansion": 0,
        "snow_white": 0,
    }
    # スクショ外のアトラクションは default_priority を使う

    constraints = RouteConstraints(
        start_time=current_time,
        close_time=close_time,
        entrance=entrance,
        fixed_blocks=fixed_blocks,
    )

    # 実 snapshot を使って再現
    import sys
    use_real = "--real" in sys.argv
    if use_real:
        snap_data = json.loads(Path("data/snapshots/2026-05-23_2116.json").read_text())
        snapshot = WaitTimeSnapshot(**snap_data)
        print(f"\n[使用 snapshot] 実データ {snapshot.timestamp} (operating={sum(1 for e in snapshot.data if e.status=='operating')}件)")
    else:
        snapshot = make_snapshot(attractions, current_time)
        print(f"\n[使用 snapshot] 合成データ ({len(snapshot.data)}件全 operating)")

    must_visits = {"pooh", "beauty_and_beast"}

    result = generate_route(
        snapshot=snapshot,
        attractions=attractions,
        constraints=constraints,
        priorities=priorities,
        must_visits=must_visits,
        visited=set(),
        weather_mode="normal",
    )

    print(f"\n=== ルートステップ {len(result.steps)} 件 ===\n")
    for step in result.steps:
        print(
            f"  {step.arrive.strftime('%H:%M')}-{step.ride_end.strftime('%H:%M')} "
            f"[{step.type:10}] {step.label or step.id} "
            f"(travel={step.travel_min}m, wait={step.wait_min}m)"
        )

    print(f"\n=== 未消化 must ===")
    print(f"  {result.unvisited_musts}")

    print(f"\n=== 警告 ===")
    for w in result.warnings:
        print(f"  [{w.kind}] {w.message}")

    print(f"\n=== 候補プール（current_time={current_time.strftime('%H:%M')}）===")
    # candidate_pool 内訳を確認
    operating_no_reserve = [
        a for a in attractions
        if not a.requires_reservation
        and priorities.get(a.id, a.default_priority) > 0
    ]
    for a in operating_no_reserve:
        p = priorities.get(a.id, a.default_priority)
        print(f"  {a.id:25} pri={p} tier={a.popularity_tier} avg={a.avg_wait_min} pass={a.pass_type}")


if __name__ == "__main__":
    main()
