"""Queue-Times の stats ページから全期間平均待ち時間をスクレイピングし、
data/attractions.json の各エントリに `avg_wait_min` を埋め込むスクリプト。

シミュレーションモード（build_opening_snapshot）の精度向上に使う。
年に一度くらいの頻度で再実行する想定（Queue-Times の集計が更新されるため）。

Usage:
    .venv/bin/python scripts/fetch_queue_times_averages.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATS_URL = "https://queue-times.com/parks/274/stats"
API_URL = "https://queue-times.com/parks/274/queue_times.json"
USER_AGENT = "Mozilla/5.0 (compatible; tdl-route-planner/1.0; personal-use)"

ATTRACTIONS_PATH = Path("data/attractions.json")


def fetch_averages_by_name() -> dict[str, int]:
    """stats ページから {ride_name: avg_min} を抽出。"""
    resp = requests.get(STATS_URL, headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text().strip().lower()
        if "average queue time by ride" in text and "all time" in text:
            table = heading.find_next("table")
            if not table:
                continue
            result: dict[str, int] = {}
            for row in table.find_all("tr")[1:]:  # skip header
                cells = [c.get_text().strip() for c in row.find_all(["td", "th"])]
                if len(cells) >= 2 and cells[1].isdigit():
                    result[cells[0]] = int(cells[1])
            return result
    raise RuntimeError("Average queue time by ride (all time) テーブルが見つかりません")


def fetch_id_to_name() -> dict[int, str]:
    """live API から {queue_times_id: name} を取得（突合用）。"""
    resp = requests.get(API_URL, headers={"User-Agent": USER_AGENT}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {r["id"]: r["name"] for r in data.get("rides", [])}


def main() -> int:
    averages = fetch_averages_by_name()
    print(f"stats から {len(averages)} 件取得")

    id_to_name = fetch_id_to_name()
    print(f"live API から {len(id_to_name)} 件取得")

    data = json.loads(ATTRACTIONS_PATH.read_text())
    updated = 0
    missing: list[str] = []
    for a in data["attractions"]:
        qt_id = a.get("queue_times_id")
        if qt_id is None:
            continue
        name_in_api = id_to_name.get(qt_id)
        if not name_in_api:
            missing.append(f"{a['id']} (qt_id={qt_id})")
            continue
        avg = averages.get(name_in_api)
        if avg is None:
            missing.append(f"{a['id']} ({name_in_api}) — stats 未収録")
            continue
        a["avg_wait_min"] = avg
        updated += 1

    ATTRACTIONS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"更新: {updated} 件 / {len(data['attractions'])}")
    if missing:
        print(f"⚠️ マッピングできなかったエントリ ({len(missing)}):")
        for m in missing:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
