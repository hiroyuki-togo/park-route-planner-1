"""TDL 公式 JSON API から待ち時間データを取得・パースする。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.models import WaitTimeEntry, WaitTimeSnapshot


TDL_JSON_URL = "https://www.tokyodisneyresort.jp/_/realtime/tdl_attraction.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CACHE_TTL_MIN = 5
REQUEST_TIMEOUT_SEC = 30


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


def _is_cache_fresh(last_fetch: datetime | None) -> bool:
    if last_fetch is None:
        return False
    return (datetime.now() - last_fetch) < timedelta(minutes=CACHE_TTL_MIN)


def _latest_snapshot_file(snapshot_dir: Path) -> Path | None:
    files = sorted(snapshot_dir.glob("*.json"))
    return files[-1] if files else None


def _load_snapshot_from_file(path: Path) -> WaitTimeSnapshot:
    raw = json.loads(path.read_text())
    return WaitTimeSnapshot.model_validate(raw)


def fetch_realtime_wait_times(
    snapshot_dir: Path = Path("data/snapshots"),
    force: bool = False,
) -> WaitTimeSnapshot | None:
    """公式 JSON API から取得し、失敗時は直近スナップショットにフォールバック。"""
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            TDL_JSON_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        entries = parse_json_to_entries(resp.text)
        snapshot = WaitTimeSnapshot(
            timestamp=datetime.now(),
            park="TDL",
            data=entries,
        )
        ts = snapshot.timestamp.strftime("%Y-%m-%d_%H%M")
        (snapshot_dir / f"{ts}.json").write_text(snapshot.model_dump_json())
        return snapshot

    except Exception:
        latest = _latest_snapshot_file(snapshot_dir)
        if latest:
            return _load_snapshot_from_file(latest)
        return None
