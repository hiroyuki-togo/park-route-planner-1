import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.models import WaitTimeEntry
from src.scraper import (
    _is_cache_fresh,
    fetch_realtime_wait_times,
    match_attraction_by_queue_times_id,
    parse_queue_times_response,
)


FIXTURE = Path(__file__).parent / "fixtures" / "queue_times_sample.json"


# ─── Queue-Times パース ────────────────────────────────


def test_parse_returns_entries():
    raw = FIXTURE.read_text(encoding="utf-8")
    entries = parse_queue_times_response(raw)
    # 5/22 朝の実データは 37 件
    assert len(entries) == 37
    for e in entries:
        assert e.name
        assert e.status in ("operating", "closed")
        assert e.queue_times_id is not None


def test_parse_status_closed_when_not_open():
    raw = '{"lands":[],"rides":[{"id":999,"name":"テスト","is_open":false,"wait_time":0,"last_updated":"2026-05-22T00:00:00.000Z"}]}'
    entries = parse_queue_times_response(raw)
    assert len(entries) == 1
    assert entries[0].status == "closed"
    assert entries[0].wait_min is None
    assert entries[0].queue_times_id == 999


def test_parse_status_operating_when_open():
    raw = '{"lands":[],"rides":[{"id":8255,"name":"美女と野獣","is_open":true,"wait_time":140,"last_updated":"2026-05-22T00:00:00.000Z"}]}'
    entries = parse_queue_times_response(raw)
    assert entries[0].status == "operating"
    assert entries[0].wait_min == 140
    assert entries[0].queue_times_id == 8255


def test_parse_known_attractions_present():
    """主要アトラクションが fixture に存在し、id が正しく拾えること。"""
    raw = FIXTURE.read_text(encoding="utf-8")
    entries = parse_queue_times_response(raw)
    by_id = {e.queue_times_id: e for e in entries}
    assert by_id[8255].name.startswith("Enchanted Tale")  # 美女と野獣
    assert by_id[8008].name == "Pooh's Hunny Hunt"
    assert by_id[8254].name == "The Happy Ride with Baymax"
    # ピーターパンはメンテ中
    assert by_id[7998].status == "closed"


# ─── マッチ ────────────────────────────────────────


def test_match_by_queue_times_id_exact():
    entries = [
        WaitTimeEntry(name="Pooh", wait_min=90, status="operating", queue_times_id=8008),
        WaitTimeEntry(name="Beast", wait_min=140, status="operating", queue_times_id=8255),
    ]
    result = match_attraction_by_queue_times_id(entries, 8008)
    assert result is not None
    assert result.name == "Pooh"


def test_match_by_queue_times_id_not_found():
    entries = [
        WaitTimeEntry(name="Pooh", wait_min=90, status="operating", queue_times_id=8008),
    ]
    result = match_attraction_by_queue_times_id(entries, 9999)
    assert result is None


def test_match_by_queue_times_id_none_input():
    """attraction.queue_times_id が None（buzz/minnie_style）の場合は None 返却。"""
    entries = [
        WaitTimeEntry(name="Pooh", wait_min=90, status="operating", queue_times_id=8008),
    ]
    result = match_attraction_by_queue_times_id(entries, None)
    assert result is None


# ─── キャッシュ ───────────────────────────────────


def test_cache_fresh_within_5min():
    last = datetime.now() - timedelta(minutes=3)
    assert _is_cache_fresh(last) is True


def test_cache_fresh_after_5min():
    last = datetime.now() - timedelta(minutes=6)
    assert _is_cache_fresh(last) is False


def test_cache_fresh_none_input():
    assert _is_cache_fresh(None) is False


# ─── fetch + フォールバック ──────────────────────────


def test_fetch_returns_cached_when_fresh():
    """前回取得から 5 分以内なら HTTP を叩かず last_snapshot を返す。"""
    cached = "sentinel"
    last_fetch = datetime.now() - timedelta(minutes=2)
    with patch("src.scraper.requests.get") as mock_get:
        result = fetch_realtime_wait_times(
            last_snapshot=cached, last_fetch=last_fetch,
        )
    assert result == "sentinel"
    mock_get.assert_not_called()


def test_fetch_uses_fallback_on_error(tmp_path):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    sample = {
        "timestamp": "2026-05-25T09:00:00",
        "park": "TDL",
        "data": [{"name": "Pooh", "wait_min": 30, "status": "operating", "queue_times_id": 8008}],
    }
    (snap_dir / "2026-05-25_0900.json").write_text(json.dumps(sample))

    with patch("src.scraper.requests.get", side_effect=Exception("network error")):
        snapshot = fetch_realtime_wait_times(snapshot_dir=snap_dir)

    assert snapshot is not None
    assert snapshot.park == "TDL"
    assert len(snapshot.data) == 1
