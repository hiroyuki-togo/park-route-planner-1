"""
TDL Route Planner - Theme v2 (Theme Park Warm, Level 1.5)

CSS injection + render_route_step() for card-style route display.

Usage in app.py:
    from theme import inject_theme, render_route_step

    st.set_page_config(...)
    inject_theme()       # Call once, immediately after set_page_config
    ...
    for i, s in enumerate(result.steps):
        render_route_step(
            s,
            area=id_to_area.get(s.id) if s.id else None,
            travel_from_prev=s.travel_min if i > 0 else None,
        )
"""
from __future__ import annotations

import streamlit as st


# =============================================================================
# Design tokens
# =============================================================================
COLORS = {
    # Base
    "bg":              "#FFF8F0",  # ivory page background
    "bg_card":         "#FFFFFF",  # card surface
    "bg_subtle":       "#FFF1E5",  # subtle warm tint (badges, sidebar, alerts)

    # Brand
    "primary":         "#D85A30",  # warm orange
    "primary_dark":    "#712B13",  # deep brown-orange (headings, primary text)
    "primary_light":   "#F5C4B3",  # light border tone
    "sub":             "#993C1D",  # secondary accent

    # Borders
    "border":          "#F5C4B3",
    "border_subtle":   "#FCE5DA",

    # Text
    "text":            "#3D2817",
    "text_muted":      "#8B6F5C",

    # Semantic
    "danger":          "#C94B4B",
    "danger_light":    "#FCE8E8",
    "neutral_border":  "#D4C5B8",
    "neutral_bg":      "#F8F4EF",

    # Type-specific accents (route cards)
    "type_attraction": "#D85A30",  # = primary
    "type_dpa":        "#8B5CF6",  # purple
    "type_meal":       "#F59E0B",  # amber
    "type_show":       "#EC4899",  # pink
}


# =============================================================================
# inject_theme
# =============================================================================
def inject_theme() -> None:
    """Inject CSS into the Streamlit app. Call once near the top of app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = f"""
<style>
/* ============================================================
   Google Fonts
   ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

/* ============================================================
   CSS variables
   ============================================================ */
:root {{
    --color-bg:            {COLORS['bg']};
    --color-bg-card:       {COLORS['bg_card']};
    --color-bg-subtle:     {COLORS['bg_subtle']};
    --color-primary:       {COLORS['primary']};
    --color-primary-dark:  {COLORS['primary_dark']};
    --color-primary-light: {COLORS['primary_light']};
    --color-sub:           {COLORS['sub']};
    --color-border:        {COLORS['border']};
    --color-border-subtle: {COLORS['border_subtle']};
    --color-text:          {COLORS['text']};
    --color-text-muted:    {COLORS['text_muted']};
    --color-danger:        {COLORS['danger']};
    --color-danger-light:  {COLORS['danger_light']};
}}

/* ============================================================
   Base
   ============================================================ */
html, body, [class*="css"] {{
    font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.stApp {{
    background-color: var(--color-bg);
    color: var(--color-text);
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
    color: var(--color-primary-dark);
    font-weight: 700;
}}

/* ============================================================
   Buttons - base reset
   ============================================================ */
.stButton > button {{
    font-family: 'Noto Sans JP', sans-serif;
    font-weight: 500;
    border-radius: 8px;
    transition: all 0.15s ease;
}}

/* ---- Tier 1: Primary (btn_gen, type="primary") ----
   Orange filled with shadow. Streamlit applies kind="primary" attr. */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
    background-color: var(--color-primary) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 2px 6px rgba(216, 90, 48, 0.3) !important;
    font-weight: 700 !important;
}}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {{
    background-color: var(--color-primary-dark) !important;
    box-shadow: 0 4px 10px rgba(216, 90, 48, 0.4) !important;
    transform: translateY(-1px);
}}

/* ---- Tier 2: Secondary (btn_fetch) ----
   White background with orange border. */
.st-key-btn_fetch .stButton > button {{
    background-color: white !important;
    color: var(--color-primary-dark) !important;
    border: 2px solid var(--color-primary) !important;
    font-weight: 500 !important;
}}
.st-key-btn_fetch .stButton > button:hover {{
    background-color: var(--color-bg-subtle) !important;
    border-color: var(--color-primary-dark) !important;
}}

/* ---- Tier 3: Neutral (btn_reset_sess) ----
   White + soft gray, low emphasis. */
.st-key-btn_reset_sess .stButton > button {{
    background-color: white !important;
    color: var(--color-text-muted) !important;
    border: 1px solid {COLORS['neutral_border']} !important;
    font-weight: 400 !important;
}}
.st-key-btn_reset_sess .stButton > button:hover {{
    background-color: {COLORS['neutral_bg']} !important;
    color: var(--color-text) !important;
}}

/* ---- Tier 4: Danger (btn_reset_full) ----
   Red outline, smaller, for irreversible actions. */
.st-key-btn_reset_full .stButton > button {{
    background-color: white !important;
    color: var(--color-danger) !important;
    border: 2px solid var(--color-danger) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.25rem 0.75rem !important;
}}
.st-key-btn_reset_full .stButton > button:hover {{
    background-color: var(--color-danger-light) !important;
    border-color: #A03333 !important;
}}

/* ---- Confirm-reset button (in inline reset dialog) ----
   Danger-styled to match the 🗑 reset_full button family.
   Filled red so the irreversible action stands out, but in
   danger color (not primary orange) to signal destruction. */
.st-key-btn_confirm_reset .stButton > button {{
    background-color: var(--color-danger) !important;
    color: white !important;
    border: 2px solid var(--color-danger) !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(201, 75, 75, 0.3) !important;
}}
.st-key-btn_confirm_reset .stButton > button:hover {{
    background-color: #A03333 !important;
    border-color: #A03333 !important;
    box-shadow: 0 4px 10px rgba(201, 75, 75, 0.4) !important;
    transform: translateY(-1px);
}}

/* ============================================================
   Alerts (st.warning - confirmation dialog)
   Override Streamlit's default yellow to warm theme.
   Covers both old (stAlert) and new (stAlertContainer) testids.
   ============================================================ */
div[data-testid="stAlertContainer"],
div[data-testid="stAlert"] {{
    background-color: var(--color-bg-subtle) !important;
    border-left: 4px solid var(--color-primary) !important;
    border-radius: 8px !important;
    color: var(--color-primary-dark) !important;
}}
div[data-testid="stAlertContainer"] *,
div[data-testid="stAlert"] * {{
    color: var(--color-primary-dark) !important;
}}

/* ============================================================
   Inputs
   ============================================================ */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTimeInput input,
.stSelectbox > div > div {{
    border-color: var(--color-border) !important;
    background-color: white !important;
}}

.stTextInput input:focus,
.stNumberInput input:focus,
.stDateInput input:focus,
.stTimeInput input:focus {{
    border-color: var(--color-primary) !important;
    box-shadow: 0 0 0 1px var(--color-primary) !important;
}}

/* ============================================================
   Hide stray input caret (vertical line) inside dropdown-style
   widgets — selectbox / time_input / date_input all wrap a
   filter input whose blinking caret leaks through.
   Targeting via ARIA roles is the most reliable: BaseWeb
   marks the inner filter input with role=combobox and
   aria-autocomplete=list regardless of Streamlit version.
   ============================================================ */
input[role="combobox"],
input[aria-autocomplete="list"],
input[aria-autocomplete="both"],
input[readonly],
[data-baseweb="select"] input,
[data-baseweb="combobox"] input,
.stTimeInput input,
.stDateInput input,
.stSelectbox input,
div[data-testid="stTimeInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] input {{
    caret-color: transparent !important;
}}

/* ============================================================
   Sidebar
   ============================================================ */
section[data-testid="stSidebar"] {{
    background-color: var(--color-bg-subtle);
    border-right: 1px solid var(--color-border);
}}

/* ============================================================
   Expander
   ============================================================ */
.streamlit-expanderHeader,
details > summary {{
    background-color: var(--color-bg-subtle);
    border-radius: 8px;
}}

/* ============================================================
   Route card (rendered via render_route_step)
   ============================================================ */
.route-card {{
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border-subtle);
    border-left: 4px solid {COLORS['type_attraction']};
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 4px;
    box-shadow: 0 1px 3px rgba(113, 43, 19, 0.06);
}}

.route-card[data-type="dpa"]    {{ border-left-color: {COLORS['type_dpa']}; }}
.route-card[data-type="meal"]   {{ border-left-color: {COLORS['type_meal']}; }}
.route-card[data-type="show"],
.route-card[data-type="parade"] {{ border-left-color: {COLORS['type_show']}; }}

.route-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 0.875rem;
    flex-wrap: wrap;
}}

.route-card-time {{
    font-weight: 700;
    color: var(--color-primary-dark);
    font-variant-numeric: tabular-nums;
    font-size: 0.95rem;
}}

.route-card-meta {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}}

.route-card-type-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    background-color: var(--color-bg-subtle);
    color: var(--color-primary-dark);
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
}}

.route-card[data-type="dpa"] .route-card-type-badge {{
    background-color: #F3EAFC;
    color: {COLORS['type_dpa']};
}}
.route-card[data-type="meal"] .route-card-type-badge {{
    background-color: #FEF3C7;
    color: #92400E;
}}
.route-card[data-type="show"] .route-card-type-badge,
.route-card[data-type="parade"] .route-card-type-badge {{
    background-color: #FCE7F3;
    color: #9D174D;
}}

.route-card-wait {{
    color: var(--color-text-muted);
    font-size: 0.8125rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}}
.route-card-wait strong {{
    color: var(--color-sub);
    font-weight: 700;
}}

.route-card-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-text);
    margin: 4px 0 2px 0;
    line-height: 1.4;
}}

.route-card-area {{
    color: var(--color-text-muted);
    font-size: 0.8125rem;
}}

.route-card-dpa-badge {{
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 4px;
    background-color: #F3EAFC;
    color: {COLORS['type_dpa']};
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    vertical-align: middle;
}}

.route-travel {{
    text-align: center;
    color: var(--color-text-muted);
    font-size: 0.8125rem;
    margin: 2px 0;
    padding: 2px 0;
    line-height: 1.4;
}}
.route-travel-arrow {{
    color: var(--color-primary-light);
    font-weight: 700;
    margin-right: 4px;
}}
</style>
"""


# =============================================================================
# render_route_step
# =============================================================================
_TYPE_CONFIG = {
    "attraction": {"icon": "🎢", "label": "アトラクション"},
    "dpa":        {"icon": "🎟", "label": "DPA"},
    "meal":       {"icon": "🍴", "label": "食事"},
    "show":       {"icon": "🎭", "label": "ショー"},
    "parade":     {"icon": "🎉", "label": "パレード"},
}


def render_route_step(
    step,
    area: str | None = None,
    travel_from_prev: float | None = None,
) -> None:
    """
    Render a single route step as a card, optionally preceded by a travel-time
    indicator from the previous step.

    Args:
        step: RouteStep instance (Pydantic model with type/arrive/ride_start/
              ride_end/wait_min/label/id/via).
        area: Area name string. Resolved on app.py side from attractions.json
              (id → area). Pass None to omit the area line.
        travel_from_prev: Travel time in minutes FROM the previous step TO this
              step. Pass None for the first step (no arrow shown).
              Conventionally this is `step.travel_min` for i > 0.

    Notes:
        - HTML escaping is applied to user-controlled fields (label, area).
        - Unknown step.type falls back to "attraction" config, but data-type
          attribute keeps the raw type string.
    """
    # ---- Travel arrow (rendered first, between cards) ----
    if travel_from_prev is not None and travel_from_prev > 0:
        st.markdown(
            f'<div class="route-travel">'
            f'<span class="route-travel-arrow">↓</span>'
            f'徒歩 約{int(round(travel_from_prev))}分'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---- Card content ----
    cfg = _TYPE_CONFIG.get(step.type, _TYPE_CONFIG["attraction"])
    title = step.label or step.id or ""
    arrive_str = step.arrive.strftime("%H:%M")

    # Ride duration (ride_end - ride_start), in minutes
    try:
        duration_min = int((step.ride_end - step.ride_start).total_seconds() / 60)
    except Exception:
        duration_min = 0
    end_str = step.ride_end.strftime("%H:%M") if getattr(step, "ride_end", None) else ""

    # Wait / duration / end-time display
    wait_min = getattr(step, "wait_min", 0) or 0
    parts: list[str] = []
    if step.type in ("attraction", "dpa"):
        if wait_min > 0:
            parts.append(f'待ち <strong>{int(wait_min)}</strong>分')
        if duration_min > 0:
            parts.append(f'体験 {duration_min}分')
    elif step.type in ("meal", "show", "parade") and duration_min > 0:
        parts.append(f'{duration_min}分')
    if end_str:
        parts.append(f'→ {end_str} 終了')

    wait_html = (
        f'<span class="route-card-wait">{" ・ ".join(parts)}</span>' if parts else ""
    )

    # DPA badge (only when the step is NOT itself a dpa-type but was experienced via DPA)
    dpa_badge_html = ""
    if getattr(step, "via", None) == "dpa" and step.type != "dpa":
        dpa_badge_html = '<span class="route-card-dpa-badge">DPA</span>'

    area_html = (
        f'<div class="route-card-area">{_escape(area)}</div>' if area else ""
    )

    card_html = (
        f'<div class="route-card" data-type="{_escape(step.type)}">'
        f'  <div class="route-card-header">'
        f'    <span class="route-card-time">{arrive_str}</span>'
        f'    <div class="route-card-meta">'
        f'      <span class="route-card-type-badge">{cfg["icon"]} {cfg["label"]}{dpa_badge_html}</span>'
        f'      {wait_html}'
        f'    </div>'
        f'  </div>'
        f'  <div class="route-card-title">{_escape(title)}</div>'
        f'  {area_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


# =============================================================================
# Helpers
# =============================================================================
def _escape(s) -> str:
    """Minimal HTML escape for user-controlled strings."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
