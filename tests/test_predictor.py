from datetime import datetime, timedelta

from src.models import Attraction
from src.predictor import predict_wait


def make_attraction(tier="S", outdoor=False):
    return Attraction(
        id="x", name="X", scrape_key="X", area="ファンタジーランド",
        lat=35.63, lng=139.88, experience_time_min=5, queue_walk_min=3,
        default_priority=5,
        requires_reservation=False, outdoor=outdoor,
        popularity_tier=tier,
    )


def test_within_30min_returns_current():
    now = datetime(2026, 5, 25, 10, 0)
    target = now + timedelta(minutes=20)
    assert predict_wait(make_attraction(), 30, now, target) == 30


def test_peak_hour_increases_wait():
    """9時(0.7)→12時(1.3) の遷移で wait が増える。"""
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    predicted = predict_wait(make_attraction("S"), 30, now, target)
    assert predicted > 30


def test_evening_decreases_wait():
    """12時(1.3)→20時(0.7) の遷移で wait が減る。"""
    now = datetime(2026, 5, 25, 12, 0)
    target = datetime(2026, 5, 25, 20, 0)
    predicted = predict_wait(make_attraction("S"), 60, now, target)
    assert predicted < 60


def test_tier_s_swings_more_than_c():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    pred_s = predict_wait(make_attraction("S"), 30, now, target)
    pred_c = predict_wait(make_attraction("C"), 30, now, target)
    assert pred_s > pred_c


def test_minimum_wait_clamped_to_5():
    now = datetime(2026, 5, 25, 12, 0)
    target = datetime(2026, 5, 25, 20, 0)
    predicted = predict_wait(make_attraction("S"), 5, now, target)
    assert predicted >= 5


def test_rain_decreases_outdoor():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    outdoor = make_attraction("S", outdoor=True)
    normal = predict_wait(outdoor, 30, now, target, weather_mode="normal")
    rain = predict_wait(outdoor, 30, now, target, weather_mode="rain")
    assert rain < normal


def test_rain_increases_indoor():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    indoor = make_attraction("S", outdoor=False)
    normal = predict_wait(indoor, 30, now, target, weather_mode="normal")
    rain = predict_wait(indoor, 30, now, target, weather_mode="rain")
    assert rain > normal
