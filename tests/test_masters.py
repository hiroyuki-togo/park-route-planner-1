"""data/attractions.json と data/restaurants.json の妥当性を検証する。"""
import json
from pathlib import Path

from src.constants import AREAS
from src.models import Attraction, Restaurant


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
