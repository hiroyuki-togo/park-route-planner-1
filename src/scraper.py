"""TDL 公式 JSON API から待ち時間データを取得・パースする。"""
from __future__ import annotations

import json

from src.models import WaitTimeEntry


def parse_json_to_entries(raw: str | list) -> list[WaitTimeEntry]:
    """JSON 文字列 or 配列からアトラクションエントリのリストを抽出する。"""
    data = json.loads(raw) if isinstance(raw, str) else raw
    entries: list[WaitTimeEntry] = []
    for item in data:
        name = (item.get("FacilityName") or "").strip()
        if not name:
            continue
        standby = item.get("StandbyTime")
        op_cd = item.get("OperatingStatusCD")
        wait_min, status = _classify(standby, op_cd)
        entries.append(WaitTimeEntry(name=name, wait_min=wait_min, status=status))
    return entries


def _classify(standby: int | None, op_cd: str | None) -> tuple[int | None, str]:
    """StandbyTime と OperatingStatusCD から (wait_min, status) を判定する。"""
    if op_cd == "002":
        return None, "closed"
    if standby is None:
        return None, "unknown"
    return int(standby), "operating"


from difflib import SequenceMatcher


def match_attraction_by_scrape_key(
    entries: list[WaitTimeEntry], scrape_key: str, threshold: float = 0.6
) -> WaitTimeEntry | None:
    """scrape_key とエントリ名をファジーマッチして最も近いものを返す。"""
    best: WaitTimeEntry | None = None
    best_score = 0.0
    for e in entries:
        score = SequenceMatcher(None, scrape_key, e.name).ratio()
        # 部分一致もボーナス
        if scrape_key in e.name:
            score += 0.3
        if score > best_score:
            best_score = score
            best = e
    return best if best_score >= threshold else None
