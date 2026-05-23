"""TDL Route Planner Streamlit App."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

from src.models import Attraction, FixedBlock, Restaurant
from src.router import RouteConstraints, generate_route
from src.scraper import fetch_realtime_wait_times
from src.simulator import build_snapshot_at
from theme import inject_theme, render_route_step


st.set_page_config(page_title="TDL Route Planner", page_icon="🎢", layout="centered")
inject_theme()


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


_DEFAULT_SESSION_STATE: dict = {
    "priorities": {},
    "must_visits": set(),
    "visited_attractions": set(),
    "meal_blocks": [],
    "show_blocks": [],
    "dpa_blocks": [],
    "weather_mode": "normal",
    "last_snapshot": None,
    "last_fetch_time": None,
    "current_route": None,
    # widget key suffix。リセットのたびに +1 して全 widget を新規扱いにする
    "reset_token": 0,
    # 「⟳ いま」ボタン押下のたびに +1 して current_time widget を新規描画させる
    "now_token": 0,
}


def _init_session_state() -> None:
    for k, v in _DEFAULT_SESSION_STATE.items():
        if k not in st.session_state:
            # set / list / dict は参照共有を避けるためコピー
            st.session_state[k] = (
                v.copy() if isinstance(v, (set, list, dict)) else v
            )


def _reset_settings(*, clear_local: bool, storage: LocalStorage, today_key: str) -> None:
    """設定リセット。clear_local=True なら localStorage の保存値も消す。

    widget の内部 state をクリアするため、reset_token をインクリメントして
    各 widget の key 末尾 suffix を変える（= 別 widget として再描画させる）。
    """
    if clear_local:
        storage.deleteItem(today_key)
    new_token = st.session_state.get("reset_token", 0) + 1
    for k, v in _DEFAULT_SESSION_STATE.items():
        st.session_state[k] = (
            v.copy() if isinstance(v, (set, list, dict)) else v
        )
    st.session_state.reset_token = new_token


def main() -> None:
    _init_session_state()

    # ─── localStorage から本日分の設定を復元 ───────────
    storage = LocalStorage()
    today_key = f"tdl_settings_{date.today().isoformat()}"

    # マスタにないアトラクション ID を localStorage から復元しないようにフィルタ
    # （buzz のようにマスタから削除された後も「必ず乗る」等が残るのを防ぐ）
    valid_attraction_ids = {a.id for a in load_attractions()}

    if not st.session_state.get("_loaded"):
        saved_raw = storage.getItem(today_key)
        if saved_raw:
            try:
                saved = (
                    json.loads(saved_raw) if isinstance(saved_raw, str) else saved_raw
                )
                for k, v in saved.items():
                    if k in ("must_visits", "visited_attractions"):
                        # マスタに存在する id だけ復元
                        st.session_state[k] = set(v) & valid_attraction_ids
                    elif k == "priorities":
                        st.session_state[k] = {
                            kk: vv for kk, vv in v.items()
                            if kk in valid_attraction_ids
                        }
                    else:
                        st.session_state[k] = v
            except Exception:
                pass
        st.session_state._loaded = True

    st.title("🎢 TDL Route Planner")

    # widget key suffix。リセット時にインクリメントされ、全 widget が新規描画される
    token = st.session_state.get("reset_token", 0)

    mode = st.radio(
        "モード",
        ["🟢 当日モード（実 API）", "🔮 シミュレーションモード"],
        horizontal=True,
        key="mode",
    )
    is_sim_mode = mode == "🔮 シミュレーションモード"

    # モード切替を検知したら、ルートと snapshot をクリアする
    # （sim = 前日叩き台 / live = 当日リアルタイム の役割分離。
    #  シミュ snapshot を当日モードで使うと予測値ベースになって意味がない）
    prev_mode = st.session_state.get("_prev_mode")
    if prev_mode is not None and prev_mode != mode:
        st.session_state.current_route = None
        st.session_state.last_snapshot = None
        st.session_state.last_fetch_time = None
        st.session_state.visited_attractions = set()
    st.session_state._prev_mode = mode

    if is_sim_mode:
        sim_date = st.date_input("想定日", value=date(2026, 5, 25))
        st.caption(
            f"📅 {sim_date.isoformat()}（シミュレーション中 — 設定は保存されません）"
        )
    else:
        sim_date = None
        st.caption(f"📅 {date.today().isoformat()}（設定は本日中だけ自動保存）")

    route_date = sim_date if is_sim_mode else date.today()

    attractions = load_attractions()
    restaurants = load_restaurants()

    if not attractions:
        st.error(
            "data/attractions.json に座標が埋まったアトラクションがありません。"
            "マスタ整備（Phase 3）を完了してください。"
        )
        return

    weather_key = f"weather_toggle_{token}"
    st.checkbox(
        "☂️ 雨天モード",
        key=weather_key,
        value=(st.session_state.weather_mode == "rain"),
    )
    st.session_state.weather_mode = (
        "rain" if st.session_state.get(weather_key) else "normal"
    )

    # ─── 現在時刻 + 現在位置（sim/live 共通） ────────────
    attraction_map = {a.id: a for a in attractions}
    col_now, col_loc = st.columns(2)
    with col_now:
        # sim モードのデフォルトは 9:00、当日モードは現在時刻
        default_time = (
            time(9, 0) if is_sim_mode
            else datetime.now().time().replace(second=0, microsecond=0)
        )
        now_token = st.session_state.get("now_token", 0)
        current_time_val = st.time_input(
            "現在時刻",
            value=default_time,
            key=f"current_time_{token}_{now_token}",
        )
        # 「⟳ いま」ボタンは当日モードのみ（sim では時刻を任意に設定する用途）
        if not is_sim_mode:
            if st.button(
                "⟳ いま",
                key=f"btn_now_{token}",
                help="現在時刻フィールドを今の時刻に戻す（時間が経って再生成する時に使う）",
            ):
                st.session_state.now_token = now_token + 1
                st.rerun()
    with col_loc:
        loc_options = ["エントランス"] + [a.id for a in attractions]
        current_loc_id = st.selectbox(
            "現在位置",
            loc_options,
            format_func=lambda x: (
                "エントランス" if x == "エントランス" else attraction_map[x].name
            ),
            key=f"current_loc_{token}",
        )

    # 閉園時刻（21:00）チェック — sim/live 両方で警告
    if current_time_val >= time(21, 0):
        st.warning(
            "⚠️ 現在時刻が閉園時刻（21:00）を過ぎています。"
            "ルート生成しても空になります。"
        )
    elif current_time_val < time(9, 0):
        st.warning(
            "⚠️ 開園時刻（9:00）前が指定されています。"
            "ルートは開園後から計算されます。"
        )

    st.write(
        f"アトラクション数：{len(attractions)} 件 / "
        f"レストラン数：{len(restaurants)} 件"
    )

    # ─── アトラクション設定 ──────────────────────────────
    with st.expander("▼ アトラクション設定", expanded=False):
        for a in sorted(attractions, key=lambda x: (x.area, x.name)):
            col_must, col_done, col_prio = st.columns([1, 1, 3])
            with col_must:
                must = st.checkbox(
                    "必ず乗る",
                    key=f"must_{a.id}_{token}",
                    value=(a.id in st.session_state.must_visits),
                )
            with col_done:
                done = st.checkbox(
                    "乗った",
                    key=f"done_{a.id}_{token}",
                    value=(a.id in st.session_state.visited_attractions),
                    help="チェックすると候補から除外され、再生成時に重複しない",
                )
            if done:
                st.session_state.visited_attractions.add(a.id)
            else:
                st.session_state.visited_attractions.discard(a.id)
            with col_prio:
                priority = st.slider(
                    a.name,
                    min_value=0, max_value=5,
                    value=st.session_state.priorities.get(a.id, a.default_priority),
                    key=f"prio_{a.id}_{token}",
                    help="0 = 乗らない（候補から除外）／1〜5 = 優先度",
                )
                if a.queue_times_id is None:
                    st.caption(
                        f"⚠️ {a.name} は Queue-Times 未収録 → 開園想定値で計算"
                    )
            st.session_state.priorities[a.id] = priority
            if must:
                st.session_state.must_visits.add(a.id)
            else:
                st.session_state.must_visits.discard(a.id)
            if must and priority == 0:
                st.warning(
                    f"⚠️ {a.name}：「必ず乗る」かつ優先度 0 は矛盾しています。必ず乗る扱いになります"
                )
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
            key=f"meal_count_{token}",
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
                    key=f"meal_rest_{i}_{token}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(12, 0)),
                    key=f"meal_start_{i}_{token}",
                )
            with cols[2]:
                end_default = time(13, 30) if i == 0 else time(19, 0)
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else end_default),
                    key=f"meal_end_{i}_{token}",
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
            key=f"show_count_{token}",
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
                    key=f"show_label_{i}_{token}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(13, 30)),
                    key=f"show_start_{i}_{token}",
                )
            with cols[2]:
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else time(14, 15)),
                    key=f"show_end_{i}_{token}",
                )
            with cols[3]:
                watch = st.checkbox(
                    "鑑賞",
                    value=(existing["watch"] if existing else False),
                    key=f"show_watch_{i}_{token}",
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
        dpa_count = st.number_input(
            "DPA 数", min_value=0, max_value=4,
            value=len(st.session_state.dpa_blocks),
            key=f"dpa_count_{token}",
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
                    key=f"dpa_attr_{i}_{token}",
                )
            with cols[1]:
                start_t = st.time_input(
                    f"開始 #{i+1}",
                    value=(time.fromisoformat(existing["start"]) if existing else time(10, 30)),
                    key=f"dpa_start_{i}_{token}",
                )
            with cols[2]:
                end_t = st.time_input(
                    f"終了 #{i+1}",
                    value=(time.fromisoformat(existing["end"]) if existing else time(11, 30)),
                    key=f"dpa_end_{i}_{token}",
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

    # ─── 取得 + ルート生成 + リセット ───────────────────
    col_fetch, col_gen, col_reset_sess, col_reset_full = st.columns([3, 3, 2, 2])
    with col_fetch:
        fetch_label = (
            "🔮 合成 snapshot 生成" if is_sim_mode else "🔄 待ち時間を取得（Queue-Times 経由）"
        )
        if st.button(fetch_label, key="btn_fetch"):
            with st.spinner("生成中..." if is_sim_mode else "取得中..."):
                if is_sim_mode:
                    snap = build_snapshot_at(
                        attractions,
                        datetime.combine(route_date, current_time_val),
                    )
                    st.session_state.last_snapshot = snap
                    st.session_state.last_fetch_time = datetime.now()
                    st.success(
                        f"合成 snapshot 生成：{sim_date.isoformat()} {current_time_val.strftime('%H:%M')} スタート想定"
                    )
                else:
                    snap = fetch_realtime_wait_times(
                        last_snapshot=st.session_state.last_snapshot,
                        last_fetch=st.session_state.last_fetch_time,
                    )
                    if snap:
                        st.session_state.last_snapshot = snap
                        st.session_state.last_fetch_time = datetime.now()
                        # snapshot.timestamp は scraper 側で既に JST naive に変換済み
                        age_min = int(
                            (datetime.now() - snap.timestamp).total_seconds() / 60
                        )
                        if age_min > 30:
                            st.warning(
                                f"⚠️ 取得成功：{snap.timestamp.strftime('%H:%M')} 時点 "
                                f"（{age_min} 分前のデータ、古い可能性。"
                                f"TDL 開園前 / 閉園後は Queue-Times 側の更新が止まります）"
                                f"  Powered by Queue-Times.com"
                            )
                        else:
                            st.success(
                                f"取得成功：{snap.timestamp.strftime('%H:%M')} 時点 "
                                f"({age_min} 分前)  Powered by Queue-Times.com"
                            )
                    else:
                        # Queue-Times も snapshot ファイルも無い → シミュ値で代替
                        fallback = build_snapshot_at(
                            attractions,
                            datetime.combine(route_date, current_time_val),
                        )
                        st.session_state.last_snapshot = fallback
                        st.session_state.last_fetch_time = datetime.now()
                        st.warning(
                            "Queue-Times に接続できませんでした。"
                            f"シミュレーション値（{current_time_val.strftime('%H:%M')} スタート想定）で代替します。"
                        )

    with col_gen:
        gen_label = (
            "🔮 シミュレーション" if is_sim_mode else "⚡ ルート生成"
        )
        if st.button(gen_label, type="primary", key="btn_gen"):
            if st.session_state.last_snapshot is None:
                st.warning(
                    "先に「合成 snapshot 生成」を押してください"
                    if is_sim_mode
                    else "先に「更新」を押してください"
                )
            else:
                fixed_blocks: list[FixedBlock] = []
                for m in st.session_state.meal_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="meal",
                        start=datetime.combine(route_date, time.fromisoformat(m["start"])),
                        end=datetime.combine(route_date, time.fromisoformat(m["end"])),
                        label=m["label"],
                        restaurant_id=m["restaurant_id"],
                        location=(m["lat"], m["lng"]),
                    ))
                for s in st.session_state.show_blocks:
                    fixed_blocks.append(FixedBlock(
                        type=s["type"],
                        start=datetime.combine(route_date, time.fromisoformat(s["start"])),
                        end=datetime.combine(route_date, time.fromisoformat(s["end"])),
                        label=s["label"],
                        watch=s["watch"],
                    ))
                for d in st.session_state.dpa_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="dpa",
                        start=datetime.combine(route_date, time.fromisoformat(d["start"])),
                        end=datetime.combine(route_date, time.fromisoformat(d["end"])),
                        label=d["label"],
                        attraction_id=d["attraction_id"],
                        location=(d["lat"], d["lng"]),
                    ))
                raw = json.loads(Path("data/attractions.json").read_text())
                entrance_coords = (raw["entrance"]["lat"], raw["entrance"]["lng"])
                if current_loc_id == "エントランス":
                    start_location = entrance_coords
                else:
                    a = attraction_map[current_loc_id]
                    start_location = (a.lat, a.lng)
                constraints = RouteConstraints(
                    start_time=datetime.combine(route_date, current_time_val),
                    close_time=datetime.combine(route_date, time(21, 0)),
                    entrance=start_location,
                    fixed_blocks=fixed_blocks,
                )
                result = generate_route(
                    snapshot=st.session_state.last_snapshot,
                    attractions=attractions,
                    constraints=constraints,
                    priorities=st.session_state.priorities,
                    must_visits=set(st.session_state.must_visits),
                    visited=set(st.session_state.visited_attractions),
                    weather_mode=st.session_state.weather_mode,
                )
                st.session_state.current_route = result

    with col_reset_sess:
        if st.button(
            "🧹 セッション",
            help="この画面の設定だけ消す。保存設定（次回起動時の復元）は残る",
            key="btn_reset_sess",
        ):
            st.session_state._pending_reset = "session"
            st.rerun()

    with col_reset_full:
        if st.button(
            "🗑 完全",
            help="保存設定（localStorage）も含めて全削除",
            key="btn_reset_full",
        ):
            st.session_state._pending_reset = "full"
            st.rerun()

    # ─── リセット確認 ──────────────────────────────────
    pending = st.session_state.get("_pending_reset")
    if pending:
        msg = (
            "セッション中の設定だけ消します（保存設定は残るので、次回起動時に復元されます）"
            if pending == "session"
            else "保存設定（localStorage）も含めて全削除します。元に戻せません"
        )
        st.warning(f"⚠️ {msg}。本当によろしいですか？")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("はい、リセット", key="btn_confirm_reset"):
                _reset_settings(
                    clear_local=(pending == "full"),
                    storage=storage,
                    today_key=today_key,
                )
                st.session_state._pending_reset = None
                st.toast("リセット完了")
                st.rerun()
        with col_no:
            if st.button("キャンセル", key="reset_no"):
                st.session_state._pending_reset = None
                st.rerun()

    # ─── 結果表示 ─────────────────────────────────────
    result = st.session_state.current_route
    if result:
        st.subheader("▼ 推奨ルート")
        id_to_area = {a.id: a.area for a in attractions}
        for i, s in enumerate(result.steps):
            render_route_step(
                s,
                area=id_to_area.get(s.id) if s.id else None,
                travel_from_prev=s.travel_min if i > 0 else None,
            )

        if result.unvisited_musts:
            unvisited_names = [
                attraction_map[m].name if m in attraction_map else m
                for m in result.unvisited_musts
            ]
            st.warning(
                "⚠️ 未消化の must-visit:\n"
                + "\n".join(f"- {n}" for n in unvisited_names)
            )

        for w in result.warnings:
            st.warning(f"⚠️ {w.message}")

        # ─── CSV 出力 ─────────────────────────────────
        df = pd.DataFrame([
            {
                "時刻": s.arrive.strftime("%H:%M"),
                "種別": s.type,
                "名前": s.label or s.id or "",
                "待ち分": int(s.wait_min) if s.wait_min else 0,
                "移動分": int(s.travel_min) if s.travel_min else 0,
            }
            for s in result.steps
        ])
        csv = df.to_csv(index=False).encode("utf-8-sig")
        csv_prefix = "route_sim_" if is_sim_mode else "route_"
        st.download_button(
            "📥 CSV 出力",
            data=csv,
            file_name=f"{csv_prefix}{route_date.isoformat()}.csv",
            mime="text/csv",
        )

    # ─── localStorage に本日分を保存（シミュ中はスキップ） ──
    if not is_sim_mode:
        to_save = {
            "priorities": st.session_state.priorities,
            "must_visits": list(st.session_state.must_visits),
            "visited_attractions": list(st.session_state.visited_attractions),
            "meal_blocks": st.session_state.meal_blocks,
            "show_blocks": st.session_state.show_blocks,
            "dpa_blocks": st.session_state.dpa_blocks,
            "weather_mode": st.session_state.weather_mode,
        }
        storage.setItem(today_key, json.dumps(to_save, ensure_ascii=False))

    # ─── フッター（クレジット要件） ─────────────────────
    st.markdown("---")
    st.caption(
        "待ち時間データ: Powered by [Queue-Times.com](https://queue-times.com/)"
    )


if __name__ == "__main__":
    main()
