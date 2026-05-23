"""Queue-Times.com から star_tours / splash_mountain の ID と avg_wait_min を抽出する 1 回限りのスクリプト。

実行後、出力をコピペして data/attractions.json に手動で反映する。
"""
from __future__ import annotations

import json

import requests

QUEUE_TIMES_URL = "https://queue-times.com/parks/274/queue_times.json"
TARGETS = {
    "star_tours": ["Star Tours", "スター・ツアーズ", "Star tours"],
    "splash_mountain": ["Splash Mountain", "スプラッシュ"],
}


def fetch_attractions() -> list[dict]:
    resp = requests.get(QUEUE_TIMES_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    out: list[dict] = []
    # Queue-Times は park によって rides をトップレベルに置く場合と lands 配下に分ける場合がある。
    # TDL (park_id=274) は 2026-05-23 時点でトップレベル rides 形式。
    for ride in data.get("rides", []):
        out.append(ride)
    for land in data.get("lands", []):
        for ride in land.get("rides", []):
            out.append(ride)
    return out


def main() -> None:
    rides = fetch_attractions()
    print(f"Queue-Times から {len(rides)} 件取得\n")
    for our_id, candidates in TARGETS.items():
        match = None
        for ride in rides:
            name = ride.get("name", "")
            for cand in candidates:
                if cand.lower() in name.lower():
                    match = ride
                    break
            if match:
                break
        if match:
            print(f"✓ {our_id}:")
            print(f"  queue_times_id = {match['id']}")
            print(f"  name (QT) = {match['name']}")
            print(f"  current wait = {match.get('wait_time', 'N/A')} 分")
            print(f"  is_open = {match.get('is_open')}")
        else:
            print(f"✗ {our_id}: 該当なし")
        print()


if __name__ == "__main__":
    main()
