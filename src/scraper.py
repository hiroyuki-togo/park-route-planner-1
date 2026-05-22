"""Queue-Times.com から待ち時間データを取得・パースする。

OLC 公式の `/_/realtime/tdl_attraction.json` は WAF で完全黙殺されるため、
第三者の集約 API である Queue-Times.com 経由で TDL（park_id=274）のデータを取得する。

クレジット要件: UI に「Powered by Queue-Times.com」のリンク表示が必須（app.py 側で対応）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.models import WaitTimeEntry, WaitTimeSnapshot

_logger = logging.getLogger(__name__)


QUEUE_TIMES_URL = "https://queue-times.com/parks/274/queue_times.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CACHE_TTL_MIN = 5
REQUEST_TIMEOUT_SEC = 10  # Queue-Times は高速応答（公式直叩きと違いタイムアウトリスク低）


# ─── パース ────────────────────────────────────────


def parse_queue_times_response(raw: str | dict) -> list[WaitTimeEntry]:
    """Queue-Times の JSON レスポンスから WaitTimeEntry のリストを抽出する。

    入力フォーマット:
        {"lands": [...], "rides": [{"id": int, "name": str,
                                    "is_open": bool, "wait_time": int,
                                    "last_updated": str(ISO 8601 UTC)}]}
    """
    data = json.loads(raw) if isinstance(raw, str) else raw
    entries: list[WaitTimeEntry] = []
    for ride in data.get("rides", []):
        is_open = bool(ride.get("is_open"))
        wait = ride.get("wait_time")
        entries.append(WaitTimeEntry(
            name=str(ride.get("name", "")).strip(),
            wait_min=int(wait) if is_open and wait is not None else None,
            status="operating" if is_open else "closed",
            queue_times_id=ride.get("id"),
        ))
    return entries


def _extract_last_updated(raw: str | dict) -> datetime:
    """Queue-Times レスポンスから last_updated を抽出（UTC → naive datetime）。"""
    data = json.loads(raw) if isinstance(raw, str) else raw
    rides = data.get("rides", [])
    if not rides:
        return datetime.now()
    # 全 ride が同一 timestamp（Queue-Times は park 単位で一括更新）
    ts_str = rides[0].get("last_updated", "")
    # ISO 8601 "2026-05-22T00:36:04.000Z" → naive datetime (UTC)
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return datetime.now()


# ─── マッチ ─────────────────────────────────────────


def match_attraction_by_queue_times_id(
    entries: list[WaitTimeEntry], qt_id: int | None,
) -> WaitTimeEntry | None:
    """Queue-Times の数値 ID で該当エントリを返す。null 入力 or 未登録は None。"""
    if qt_id is None:
        return None
    for e in entries:
        if e.queue_times_id == qt_id:
            return e
    return None


# ─── キャッシュ / フォールバック ─────────────────────


def _is_cache_fresh(last_fetch: datetime | None) -> bool:
    """前回取得から CACHE_TTL_MIN 分以内なら True。"""
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
    last_snapshot: WaitTimeSnapshot | None = None,
    last_fetch: datetime | None = None,
) -> WaitTimeSnapshot | None:
    """Queue-Times API から取得し、失敗時は直近スナップショットにフォールバック。

    last_fetch が CACHE_TTL_MIN 内であれば、HTTP を叩かず last_snapshot を返す
    （ボタン連打で第三者 API を叩きすぎないため）。
    """
    if _is_cache_fresh(last_fetch) and last_snapshot is not None:
        _logger.info("returning cached snapshot (within %d min)", CACHE_TTL_MIN)
        return last_snapshot

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            QUEUE_TIMES_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        entries = parse_queue_times_response(resp.text)
        snapshot = WaitTimeSnapshot(
            timestamp=_extract_last_updated(resp.text),
            park="TDL",
            data=entries,
        )
        ts = snapshot.timestamp.strftime("%Y-%m-%d_%H%M")
        (snapshot_dir / f"{ts}.json").write_text(snapshot.model_dump_json())
        return snapshot

    except Exception as e:
        _logger.warning(
            "fetch_realtime_wait_times failed: %s: %s",
            type(e).__name__, e,
        )
        latest = _latest_snapshot_file(snapshot_dir)
        if latest:
            _logger.info("falling back to snapshot %s", latest.name)
            return _load_snapshot_from_file(latest)
        return None
