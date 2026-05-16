from pathlib import Path

from src.models import WaitTimeEntry
from src.scraper import match_attraction_by_scrape_key, parse_json_to_entries


FIXTURE = Path(__file__).parent / "fixtures" / "sample_realtime.json"


def test_parse_returns_entries():
    raw = FIXTURE.read_text(encoding="utf-8")
    entries = parse_json_to_entries(raw)
    assert len(entries) > 5
    for e in entries:
        assert e.name
        assert e.status in ("operating", "closed", "unknown")


def test_parse_status_closed_when_operating_status_cd_002():
    raw = '[{"FacilityName": "テスト", "StandbyTime": null, "OperatingStatusCD": "002", "OperatingStatus": "案内終了"}]'
    entries = parse_json_to_entries(raw)
    assert len(entries) == 1
    assert entries[0].status == "closed"
    assert entries[0].wait_min is None


def test_parse_status_operating_when_standby_time_present():
    raw = '[{"FacilityName": "テスト", "StandbyTime": 30, "OperatingStatusCD": "001", "OperatingStatus": "運営中"}]'
    entries = parse_json_to_entries(raw)
    assert entries[0].status == "operating"
    assert entries[0].wait_min == 30


def test_parse_status_unknown_when_no_data():
    raw = '[{"FacilityName": "テスト", "StandbyTime": null, "OperatingStatusCD": "003", "OperatingStatus": "運営状況確認中"}]'
    entries = parse_json_to_entries(raw)
    assert entries[0].status == "unknown"
    assert entries[0].wait_min is None


def test_fuzzy_match_exact():
    entries = [
        WaitTimeEntry(name="プーさんのハニーハント", wait_min=30, status="operating"),
        WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=45, status="operating"),
    ]
    result = match_attraction_by_scrape_key(entries, "プーさん")
    assert result.name == "プーさんのハニーハント"


def test_fuzzy_match_none():
    entries = [
        WaitTimeEntry(name="プーさん", wait_min=30, status="operating"),
    ]
    result = match_attraction_by_scrape_key(entries, "存在しないアトラクション")
    assert result is None


import json
from datetime import datetime, timedelta
from unittest.mock import patch

from src.scraper import fetch_realtime_wait_times, _is_cache_fresh


def test_cache_fresh_within_5min():
    last = datetime.now() - timedelta(minutes=3)
    assert _is_cache_fresh(last) is True


def test_cache_fresh_after_5min():
    last = datetime.now() - timedelta(minutes=6)
    assert _is_cache_fresh(last) is False


def test_fetch_uses_fallback_on_error(tmp_path):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    sample = {
        "timestamp": "2026-05-25T09:00:00",
        "park": "TDL",
        "data": [{"name": "プーさん", "wait_min": 30, "status": "operating"}],
    }
    (snap_dir / "2026-05-25_0900.json").write_text(json.dumps(sample))

    with patch("src.scraper.requests.get", side_effect=Exception("network error")):
        snapshot = fetch_realtime_wait_times(snapshot_dir=snap_dir, force=True)

    assert snapshot is not None
    assert snapshot.park == "TDL"
    assert len(snapshot.data) == 1
