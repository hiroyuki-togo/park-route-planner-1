"""動作確認用のダミー WaitTimeSnapshot を生成する。

ライブ API がレート制限等で応答しない時に、ローカルでルート生成までの
動作を確認するためのフォールバック素材を作る。

使い方:
    .venv/bin/python scripts/generate_dummy_snapshot.py

attractions.json から全アトラクション名を読み込み、人気度に応じた
それっぽい wait_min を割り当てて data/snapshots/ 配下に保存する。
出力ファイル名は scraper.py の保存形式と同じ {YYYY-MM-DD}_{HHMM}.json。
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path


# 人気度別のベース待ち時間（分）。±10 分のジッタを乗せる
BASE_WAIT_BY_TIER = {"S": 60, "A": 35, "B": 20, "C": 10}


def main() -> None:
    random.seed(42)
    project_root = Path(__file__).resolve().parents[1]
    attractions_path = project_root / "data" / "attractions.json"
    snapshots_dir = project_root / "data" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    attractions = json.loads(attractions_path.read_text())["attractions"]

    entries = []
    for a in attractions:
        base = BASE_WAIT_BY_TIER.get(a["popularity_tier"], 15)
        wait = max(5, base + random.randint(-10, 15))
        entries.append({
            "name": a["name"],
            "wait_min": wait,
            "status": "operating",
        })

    now = datetime.now()
    snapshot = {
        "timestamp": now.isoformat(timespec="seconds"),
        "park": "TDL",
        "data": entries,
    }
    filename = f"{now.strftime('%Y-%m-%d_%H%M')}_dummy.json"
    output_path = snapshots_dir / filename
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"Wrote {output_path}")
    print(f"  entries: {len(entries)} / timestamp: {snapshot['timestamp']}")


if __name__ == "__main__":
    main()
