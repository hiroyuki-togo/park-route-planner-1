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


def test_popularity_factor_keys():
    assert set(POPULARITY_FACTOR.keys()) == {"S", "A", "B", "C"}


def test_areas_seven():
    assert len(AREAS) == 7
    assert "ワールドバザール" in AREAS


def test_main_street_pairs_is_frozenset():
    for pair in MAIN_STREET_BLOCKING_PAIRS:
        assert isinstance(pair, frozenset)
        assert len(pair) == 2
