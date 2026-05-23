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
        default_priority=4, pass_type="dpa",
        requires_reservation=False, outdoor=False,
        popularity_tier="S",
    )
    assert a.id == "pooh"


def test_attraction_pass_type_dpa():
    attr = Attraction(
        id="test_dpa",
        name="Test DPA",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        pass_type="dpa",
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type == "dpa"


def test_attraction_pass_type_priority():
    attr = Attraction(
        id="test_priority",
        name="Test Priority",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        pass_type="priority",
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type == "priority"


def test_attraction_pass_type_default_none():
    attr = Attraction(
        id="test_none",
        name="Test None",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type is None


def test_attraction_pass_type_invalid_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Attraction(
            id="test_invalid",
            name="Test Invalid",
            scrape_key="Test",
            area="Test Area",
            lat=35.63,
            lng=139.88,
            experience_time_min=5,
            queue_walk_min=2,
            default_priority=3,
            pass_type="freepass",
            outdoor=False,
            popularity_tier="A",
        )


def test_attraction_tier_validation():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Attraction(
            id="x", name="x", scrape_key="x", area="x",
            lat=0, lng=0, experience_time_min=1, queue_walk_min=1,
            default_priority=1,
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
