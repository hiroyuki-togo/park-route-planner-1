"""TDL Route Planner Streamlit App."""
from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import streamlit as st

from src.models import Attraction, Restaurant


st.set_page_config(page_title="TDL Route Planner", page_icon="🎢", layout="centered")


@st.cache_data
def load_attractions() -> list[Attraction]:
    raw = json.loads(Path("data/attractions.json").read_text())
    return [
        Attraction.model_validate(a)
        for a in raw["attractions"]
        if a["lat"] is not None and a["lng"] is not None
    ]


@st.cache_data
def load_restaurants() -> list[Restaurant]:
    raw = json.loads(Path("data/restaurants.json").read_text())
    return [
        Restaurant.model_validate(r)
        for r in raw["restaurants"]
        if r["lat"] is not None and r["lng"] is not None
    ]


def _init_session_state() -> None:
    defaults = {
        "priorities": {},
        "must_visits": set(),
        "meal_blocks": [],
        "show_blocks": [],
        "dpa_blocks": [],
        "weather_mode": "normal",
        "last_snapshot": None,
        "last_fetch_time": None,
        "current_route": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def main() -> None:
    _init_session_state()
    st.title("🎢 TDL Route Planner")
    st.caption(f"📅 {date.today().isoformat()}（設定は本日中だけ自動保存）")

    attractions = load_attractions()
    restaurants = load_restaurants()

    if not attractions:
        st.error(
            "data/attractions.json に座標が埋まったアトラクションがありません。"
            "マスタ整備（Phase 3）を完了してください。"
        )
        return

    st.checkbox(
        "☂️ 雨天モード",
        key="weather_toggle",
        value=(st.session_state.weather_mode == "rain"),
    )
    st.session_state.weather_mode = (
        "rain" if st.session_state.get("weather_toggle") else "normal"
    )

    st.write(
        f"アトラクション数：{len(attractions)} 件 / "
        f"レストラン数：{len(restaurants)} 件"
    )


if __name__ == "__main__":
    main()
