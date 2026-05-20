"""TDL Route Planner Streamlit App."""
from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import streamlit as st

from src.models import Attraction, FixedBlock, Restaurant
from src.router import RouteConstraints, generate_route
from src.scraper import fetch_realtime_wait_times


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

    # ─── アトラクション設定 ──────────────────────────────
    with st.expander("▼ アトラクション設定", expanded=False):
        for a in sorted(attractions, key=lambda x: (x.area, x.name)):
            col1, col2 = st.columns([1, 3])
            with col1:
                must = st.checkbox(
                    "必ず乗る",
                    key=f"must_{a.id}",
                    value=(a.id in st.session_state.must_visits),
                )
            with col2:
                priority = st.slider(
                    a.name,
                    min_value=0, max_value=5,
                    value=st.session_state.priorities.get(a.id, a.default_priority),
                    key=f"prio_{a.id}",
                    help="0 = 乗らない（候補から除外）／1〜5 = 優先度",
                )
            st.session_state.priorities[a.id] = priority
            if must:
                st.session_state.must_visits.add(a.id)
            else:
                st.session_state.must_visits.discard(a.id)
            if a.requires_reservation and must:
                dpa_ids = {b["attraction_id"] for b in st.session_state.dpa_blocks}
                if a.id not in dpa_ids:
                    st.warning(
                        f"⚠️ {a.name} は予約必須です。DPA を登録してください。"
                    )

    # ─── 食事ブロック ──────────────────────────────────
    with st.expander("▼ 食事ブロック", expanded=False):
        meal_count = st.number_input(
            "食事の数", min_value=0, max_value=4,
            value=len(st.session_state.meal_blocks) or 2,
        )
        new_meals: list[dict] = []
        rest_map = {r.id: r for r in restaurants}
        rest_options = ["（未選択）"] + [r.id for r in restaurants]
        for i in range(int(meal_count)):
            cols = st.columns([3, 2, 2])
            existing = (
                st.session_state.meal_blocks[i]
                if i < len(st.session_state.meal_blocks) else None
            )
            with cols[0]:
                rid = st.selectbox(
                    f"店 #{i+1}",
                    rest_options,
                    format_func=lambda x: "（未選択）" if x == "（未選択）" else rest_map[x].name,
                    index=(
                        rest_options.index(existing["restaurant_id"])
                        if existing and existing.get("restaurant_id") in rest_options else 0
                    ),
                    key=f"meal_rest_{i}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(12, 0)),
                    key=f"meal_start_{i}",
                )
            with cols[2]:
                end_default = time(13, 30) if i == 0 else time(19, 0)
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else end_default),
                    key=f"meal_end_{i}",
                )
            if rid != "（未選択）":
                r = rest_map[rid]
                new_meals.append({
                    "restaurant_id": rid,
                    "label": r.name,
                    "start": start_t.isoformat(timespec="minutes"),
                    "end": end_t.isoformat(timespec="minutes"),
                    "lat": r.lat,
                    "lng": r.lng,
                })
        st.session_state.meal_blocks = new_meals

    # ─── ショー / パレード ──────────────────────────────
    with st.expander("▼ ショー・パレード", expanded=False):
        show_count = st.number_input(
            "ショー/パレードの数", min_value=0, max_value=5,
            value=len(st.session_state.show_blocks),
        )
        new_shows: list[dict] = []
        for i in range(int(show_count)):
            cols = st.columns([3, 2, 2, 2])
            existing = (
                st.session_state.show_blocks[i]
                if i < len(st.session_state.show_blocks) else None
            )
            with cols[0]:
                label = st.text_input(
                    f"ラベル #{i+1}",
                    value=(existing["label"] if existing else "パレード"),
                    key=f"show_label_{i}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(13, 30)),
                    key=f"show_start_{i}",
                )
            with cols[2]:
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else time(14, 15)),
                    key=f"show_end_{i}",
                )
            with cols[3]:
                watch = st.checkbox(
                    "鑑賞",
                    value=(existing["watch"] if existing else False),
                    key=f"show_watch_{i}",
                )
            new_shows.append({
                "type": "parade" if "パレード" in label else "show",
                "label": label,
                "start": start_t.isoformat(timespec="minutes"),
                "end": end_t.isoformat(timespec="minutes"),
                "watch": watch,
            })
        st.session_state.show_blocks = new_shows

    # ─── DPA 予約 ──────────────────────────────────────
    with st.expander("▼ DPA 予約", expanded=False):
        attraction_map = {a.id: a for a in attractions}
        dpa_count = st.number_input(
            "DPA 数", min_value=0, max_value=4,
            value=len(st.session_state.dpa_blocks),
        )
        new_dpa: list[dict] = []
        dpa_options = ["（未選択）"] + [a.id for a in attractions if a.dpa_eligible]
        for i in range(int(dpa_count)):
            cols = st.columns([3, 2, 2])
            existing = (
                st.session_state.dpa_blocks[i]
                if i < len(st.session_state.dpa_blocks) else None
            )
            with cols[0]:
                aid = st.selectbox(
                    f"アトラクション #{i+1}",
                    dpa_options,
                    format_func=lambda x: "（未選択）" if x == "（未選択）" else attraction_map[x].name,
                    index=(
                        dpa_options.index(existing["attraction_id"])
                        if existing and existing.get("attraction_id") in dpa_options else 0
                    ),
                    key=f"dpa_attr_{i}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(10, 30)),
                    key=f"dpa_start_{i}",
                )
            with cols[2]:
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else time(11, 30)),
                    key=f"dpa_end_{i}",
                )
            if aid != "（未選択）":
                a = attraction_map[aid]
                new_dpa.append({
                    "attraction_id": aid,
                    "label": f"DPA: {a.name}",
                    "start": start_t.isoformat(timespec="minutes"),
                    "end": end_t.isoformat(timespec="minutes"),
                    "lat": a.lat,
                    "lng": a.lng,
                })
        st.session_state.dpa_blocks = new_dpa

    # ─── 取得 + ルート生成 ────────────────────────────
    col_fetch, col_gen = st.columns(2)
    with col_fetch:
        if st.button("🔄 更新（待ち時間取得）"):
            with st.spinner("取得中..."):
                snap = fetch_realtime_wait_times()
                if snap:
                    st.session_state.last_snapshot = snap
                    st.session_state.last_fetch_time = datetime.now()
                    st.success(f"取得成功：{snap.timestamp.strftime('%H:%M')}")
                else:
                    st.error(
                        "取得に失敗しました（API 応答なし & フォールバック先のスナップショットも見つかりません）。"
                        "詳細は streamlit 起動ターミナルのログを確認してください。"
                    )

    with col_gen:
        if st.button("⚡ ルート生成", type="primary"):
            if st.session_state.last_snapshot is None:
                st.warning("先に「更新」を押してください")
            else:
                today = date.today()
                fixed_blocks: list[FixedBlock] = []
                for m in st.session_state.meal_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="meal",
                        start=datetime.combine(today, time.fromisoformat(m["start"])),
                        end=datetime.combine(today, time.fromisoformat(m["end"])),
                        label=m["label"],
                        restaurant_id=m["restaurant_id"],
                        location=(m["lat"], m["lng"]),
                    ))
                for s in st.session_state.show_blocks:
                    fixed_blocks.append(FixedBlock(
                        type=s["type"],
                        start=datetime.combine(today, time.fromisoformat(s["start"])),
                        end=datetime.combine(today, time.fromisoformat(s["end"])),
                        label=s["label"],
                        watch=s["watch"],
                    ))
                for d in st.session_state.dpa_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="dpa",
                        start=datetime.combine(today, time.fromisoformat(d["start"])),
                        end=datetime.combine(today, time.fromisoformat(d["end"])),
                        label=d["label"],
                        attraction_id=d["attraction_id"],
                        location=(d["lat"], d["lng"]),
                    ))
                raw = json.loads(Path("data/attractions.json").read_text())
                constraints = RouteConstraints(
                    start_time=datetime.combine(today, time(9, 0)),
                    close_time=datetime.combine(today, time(21, 0)),
                    entrance=(raw["entrance"]["lat"], raw["entrance"]["lng"]),
                    fixed_blocks=fixed_blocks,
                )
                result = generate_route(
                    snapshot=st.session_state.last_snapshot,
                    attractions=attractions,
                    constraints=constraints,
                    priorities=st.session_state.priorities,
                    must_visits=set(st.session_state.must_visits),
                    weather_mode=st.session_state.weather_mode,
                )
                st.session_state.current_route = result

    # ─── 結果表示 ─────────────────────────────────────
    result = st.session_state.current_route
    if result:
        st.subheader("▼ 推奨ルート")
        for s in result.steps:
            icon = {
                "attraction": "🎢", "meal": "🍴", "show": "🎭",
                "parade": "🎉", "dpa": "🎟",
            }[s.type]
            label = s.label or s.id or ""
            line = f"{s.arrive.strftime('%H:%M')} {icon} {label}"
            if s.wait_min:
                line += f"（待ち {int(s.wait_min)} 分）"
            st.write(line)

        if result.unvisited_musts:
            st.warning(
                "⚠️ 未消化の must-visit:\n"
                + "\n".join(f"- {m}" for m in result.unvisited_musts)
            )

        for w in result.warnings:
            st.warning(f"⚠️ {w.message}")


if __name__ == "__main__":
    main()
