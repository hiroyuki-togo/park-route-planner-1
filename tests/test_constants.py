from src.constants import (
    TIME_FACTOR, POPULARITY_FACTOR, AREAS,
    OPEN_TIME, CLOSE_TIME,
    PARK_FACTOR_NORMAL, PARK_FACTOR_RAIN,
    WALKING_SPEED_M_PER_MIN,
    MAIN_STREET_BLOCKING_PAIRS,
    get_time_factor,
)


def test_time_factor_peak():
    assert get_time_factor(12) == 1.3


def test_time_factor_morning():
    assert get_time_factor(9) == 0.7


def test_time_factor_evening():
    assert get_time_factor(20) == 0.7


def test_time_factor_before_open_defensive():
    # hour < 9 は朝の帯 (0.7) と同じ値を返す（フォールスルー 1.0 を防ぐ）
    assert get_time_factor(8) == 0.7
    assert get_time_factor(0) == 0.7


def test_time_factor_after_close_defensive():
    # hour >= 21 は夕方の帯 (0.7) と同じ値を返す（フォールスルー 1.0 を防ぐ）
    assert get_time_factor(21) == 0.7
    assert get_time_factor(23) == 0.7


def test_popularity_factor_keys():
    assert set(POPULARITY_FACTOR.keys()) == {"S", "A", "B", "C"}


def test_areas_seven():
    assert len(AREAS) == 7
    assert "ワールドバザール" in AREAS


def test_main_street_pairs_is_frozenset():
    for pair in MAIN_STREET_BLOCKING_PAIRS:
        assert isinstance(pair, frozenset)
        assert len(pair) == 2


def test_time_factor_floor_value():
    from src.constants import TIME_FACTOR_FLOOR
    assert TIME_FACTOR_FLOOR == 0.9


def test_time_factor_avg_effective_value():
    from src.constants import TIME_FACTOR_AVG_EFFECTIVE
    # (0.9 + 0.9 + 1.3*3 + 1.2*3 + 1.0*2 + 0.9*2) / 12 = 13.1/12 ≈ 1.0917
    assert TIME_FACTOR_AVG_EFFECTIVE == 13.1 / 12
    assert 1.09 < TIME_FACTOR_AVG_EFFECTIVE < 1.10
