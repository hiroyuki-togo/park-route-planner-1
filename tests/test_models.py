import pytest
from datetime import datetime, time

from src.models import (
    Attraction, Restaurant, FixedBlock, DpaReservation,
    RouteStep, RouteResult, WaitTimeSnapshot, WaitTimeEntry, Warning,
)


def test_attraction_valid():
    a = Attraction(
        id="pooh", name="プーさんのハニーハント", scrape_key="プーさん",
        area="ファンタジーランド", lat=35.63, lng=139.88,
        experience_time_min=5, queue_walk_min=3,
        default_priority=4, dpa_eligible=True,
        requires_reservation=False, outdoor=False,
        popularity_tier="S",
    )
    assert a.id == "pooh"


def test_attraction_tier_validation():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Attraction(
            id="x", name="x", scrape_key="x", area="x",
            lat=0, lng=0, experience_time_min=1, queue_walk_min=1,
            default_priority=1, dpa_eligible=False,
            requires_reservation=False, outdoor=False,
            popularity_tier="X",  # invalid
        )


def test_fixed_block_dpa_needs_attraction_id():
    block = FixedBlock(
        type="dpa",
        start=datetime(2026, 5, 25, 10, 30),
        end=datetime(2026, 5, 25, 11, 30),
        label="DPA: 美女と野獣",
        attraction_id="beauty_and_beast",
        location=(35.63, 139.88),
    )
    assert block.attraction_id == "beauty_and_beast"


def test_dpa_reservation():
    r = DpaReservation(
        attraction_id="beauty_and_beast",
        start=time(10, 30), end=time(11, 30),
    )
    assert r.start.hour == 10


def test_route_result_empty():
    r = RouteResult(steps=[], unvisited_musts=[], warnings=[])
    assert r.steps == []
