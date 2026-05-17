from datetime import datetime

from src.distance import travel_time_min
from src.models import FixedBlock


# 同エリア内（プーさん→ホーンテッドマンション、目安50m）
LOC_A = (35.6330, 139.8810)
LOC_B = (35.6333, 139.8815)
# 城を跨ぐ移動（トゥモローランド→アドベンチャーランド）
LOC_TOMORROW = (35.6320, 139.8830)
LOC_ADVENTURE = (35.6315, 139.8790)


def test_short_distance_normal():
    t = travel_time_min(LOC_A, LOC_B, current_time=datetime(2026, 5, 25, 12, 0), fixed_blocks=[])
    assert 0 < t < 5


def test_rain_increases_time():
    base = travel_time_min(LOC_A, LOC_B, datetime(2026, 5, 25, 12, 0), [], weather_mode="normal")
    rain = travel_time_min(LOC_A, LOC_B, datetime(2026, 5, 25, 12, 0), [], weather_mode="rain")
    assert rain > base


def test_parade_penalty_applies():
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=False,
    )
    base = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    with_parade = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    assert with_parade >= base + 15


def test_parade_watch_no_penalty():
    """watch=True のパレードは鑑賞中であり、横断ペナルティは無関係。"""
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=True,
    )
    base = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    with_parade = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    assert with_parade == base
