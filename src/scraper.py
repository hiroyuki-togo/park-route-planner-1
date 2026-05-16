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
