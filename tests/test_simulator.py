"""シミュレーションモード（合成 snapshot 生成）のテスト。"""
from datetime import date, datetime, time

from src.models import WaitTimeSnapshot
from src.simulator import OPENING_BASE_WAIT_BY_TIER, build_opening_snapshot


def test_opening_snapshot_basic(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))

    assert isinstance(snap, WaitTimeSnapshot)
    assert all(e.status == "operating" for e in snap.data)
    for entry, attr in zip(snap.data, sample_attractions):
        assert entry.name == attr.name
        assert entry.wait_min == OPENING_BASE_WAIT_BY_TIER[attr.popularity_tier]


def test_opening_snapshot_timestamp(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))

    assert snap.timestamp.date() == date(2026, 5, 25)
    assert snap.timestamp.time() == time(9, 0)
    assert snap.park == "TDL"


def test_opening_snapshot_count(sample_attractions):
    snap = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    assert len(snap.data) == len(sample_attractions)


def test_opening_snapshot_determinism(sample_attractions):
    snap_a = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    snap_b = build_opening_snapshot(sample_attractions, date(2026, 5, 25))
    assert snap_a == snap_b


def test_opening_snapshot_empty_attractions():
    snap = build_opening_snapshot([], date(2026, 5, 25))
    assert isinstance(snap, WaitTimeSnapshot)
    assert snap.data == []
    assert snap.timestamp == datetime(2026, 5, 25, 9, 0)
