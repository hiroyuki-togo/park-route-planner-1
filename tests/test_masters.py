"""data/attractions.json と data/restaurants.json の妥当性を検証する。"""
import json
from pathlib import Path

import pytest

from src.constants import AREAS
from src.models import Attraction, Restaurant


@pytest.fixture
def attractions_data():
    return json.loads(Path("data/attractions.json").read_text())


def test_attractions_all_loadable():
    raw = json.loads(Path("data/attractions.json").read_text())
    for a in raw["attractions"]:
        # lat/lng が埋まっていればモデル化できる
        if a["lat"] is not None and a["lng"] is not None:
            Attraction.model_validate(a)


def test_attractions_areas_valid():
    raw = json.loads(Path("data/attractions.json").read_text())
    for a in raw["attractions"]:
        assert a["area"] in AREAS, f"unknown area: {a['area']} for {a['id']}"


def test_attractions_unique_ids():
    raw = json.loads(Path("data/attractions.json").read_text())
    ids = [a["id"] for a in raw["attractions"]]
    assert len(ids) == len(set(ids)), "duplicate attraction ids"


def test_attractions_coordinates_filled():
    """全アトラクションの lat/lng が埋まっていることを確認（マスタ整備完了の DoD）。"""
    raw = json.loads(Path("data/attractions.json").read_text())
    unfilled = [a["id"] for a in raw["attractions"] if a["lat"] is None or a["lng"] is None]
    assert unfilled == [], f"coordinates missing for: {unfilled}"


def test_restaurants_all_loadable():
    raw = json.loads(Path("data/restaurants.json").read_text())
    for r in raw["restaurants"]:
        if r["lat"] is not None and r["lng"] is not None:
            Restaurant.model_validate(r)


def test_restaurants_coordinates_filled():
    raw = json.loads(Path("data/restaurants.json").read_text())
    unfilled = [r["id"] for r in raw["restaurants"] if r["lat"] is None or r["lng"] is None]
    assert unfilled == [], f"coordinates missing for: {unfilled}"


def test_star_tours_and_splash_mountain_exist(attractions_data):
    ids = {a["id"] for a in attractions_data["attractions"]}
    assert "star_tours" in ids, "スター・ツアーズが attractions.json に無い"
    assert "splash_mountain" in ids, "スプラッシュマウンテンが attractions.json に無い"


def test_pass_type_values_are_valid(attractions_data):
    for a in attractions_data["attractions"]:
        pass_type = a.get("pass_type")
        assert pass_type in (None, "dpa", "priority"), (
            f"{a['id']} の pass_type が不正: {pass_type}"
        )


def test_dpa_attractions_count(attractions_data):
    dpa = [a for a in attractions_data["attractions"] if a.get("pass_type") == "dpa"]
    assert len(dpa) == 3, f"DPA 対象は 3 件のはずだが {len(dpa)} 件"
    dpa_ids = {a["id"] for a in dpa}
    assert dpa_ids == {"beauty_and_beast", "baymax", "splash_mountain"}


def test_priority_pass_attractions_count(attractions_data):
    pri = [a for a in attractions_data["attractions"] if a.get("pass_type") == "priority"]
    assert len(pri) == 5, f"プライオリティ対象は 5 件のはずだが {len(pri)} 件"
    pri_ids = {a["id"] for a in pri}
    assert pri_ids == {
        "big_thunder",
        "pooh",
        "haunted_mansion",
        "star_tours",
        "monsters_inc",
    }
