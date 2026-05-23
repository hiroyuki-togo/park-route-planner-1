# シミュレーションモード時刻軸拡張 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** シミュレーションモードを「9:00 開園固定」から「任意時刻スタート + 時刻別補正された合成 snapshot」に拡張し、5/25 来園日までに Phase 7 デプロイへ繋げる。

**Architecture:** [src/simulator.py](../../../src/simulator.py) の `build_opening_snapshot(attractions, target_date)` を `build_snapshot_at(attractions, target_datetime)` に置換し、`avg_wait_min × max(0.9, factor) / (13.1/12)` で wait_min を時刻補正。[app.py](../../../app.py) の sim mode UI を当日モードと同じ「現在時刻 / 現在位置 / 乗った」入力を開放し、`is_sim_mode` 分岐を最小化する。既存 predictor / router には触らない。

**Tech Stack:** Python 3.11 / Streamlit / pytest / Pydantic（既存）

**Related spec:** [2026-05-23-sim-time-axis-design.md](../specs/2026-05-23-sim-time-axis-design.md)

---

## File Structure

| ファイル | 種別 | 役割 |
|---|---|---|
| [src/constants.py](../../../src/constants.py) | 修正 | `TIME_FACTOR_FLOOR = 0.9` と `TIME_FACTOR_AVG_EFFECTIVE = 13.1 / 12` を追加 |
| [src/simulator.py](../../../src/simulator.py) | 置換 | `build_opening_snapshot` を削除し `build_snapshot_at(attractions, target_datetime)` を実装 |
| [app.py](../../../app.py) | 修正 | sim mode の「現在時刻 / 現在位置 / 乗った」UI 開放、`build_snapshot_at` 呼び出し、警告拡張 |
| [tests/test_simulator.py](../../../tests/test_simulator.py) | 更新 + 追加 | 既存 6 件を新 API に置換 + 新規 3 件追加（時刻別 / 下限保護 / null フォールバック） |
| [tests/test_constants.py](../../../tests/test_constants.py) | 追加 | 新定数 2 件のテスト追加 |
| [PROGRESS.md](../../../PROGRESS.md) | 更新 | 実装完了反映 + Phase 7 着手前タスク完了として記録 |
| [lessons.md](../../../lessons.md) | 更新 | #18（役割重複）に追記 |

---

## Task 1: 新定数 `TIME_FACTOR_FLOOR` / `TIME_FACTOR_AVG_EFFECTIVE` の追加

**Files:**
- Modify: [src/constants.py](../../../src/constants.py)
- Test: [tests/test_constants.py](../../../tests/test_constants.py)

仕様の §3.1 参照。

- [ ] **Step 1: 失敗するテストを書く**

Append to `tests/test_constants.py`:

```python
def test_time_factor_floor_value():
    from src.constants import TIME_FACTOR_FLOOR
    assert TIME_FACTOR_FLOOR == 0.9


def test_time_factor_avg_effective_value():
    from src.constants import TIME_FACTOR_AVG_EFFECTIVE
    # (0.9 + 0.9 + 1.3*3 + 1.2*3 + 1.0*2 + 0.9*2) / 12 = 13.1/12 ≈ 1.0917
    assert TIME_FACTOR_AVG_EFFECTIVE == 13.1 / 12
    assert 1.09 < TIME_FACTOR_AVG_EFFECTIVE < 1.10
```

- [ ] **Step 2: テストを走らせて FAIL を確認**

Run: `.venv/bin/pytest tests/test_constants.py::test_time_factor_floor_value tests/test_constants.py::test_time_factor_avg_effective_value -v`
Expected: 2 件とも `ImportError` で FAIL（定数未定義）

- [ ] **Step 3: src/constants.py に定数を追加**

`OPENING_BASE_WAIT_BY_TIER` 行（line 38 付近）の直下に追加:

```python
# シミュレーションモードの合成 snapshot で使う、TIME_FACTOR の下限保護値。
# 「営業時間中、最も空いてる時間帯（朝・夜）でも、人気アトラクションは
# avg の 80% 以上は並ぶ」という観察則を仮定。
TIME_FACTOR_FLOOR = 0.9

# TIME_FACTOR_FLOOR を適用した後の営業時間 (9-21) における係数の加重平均。
# (0.9 + 0.9 + 1.3*3 + 1.2*3 + 1.0*2 + 0.9*2) / 12 = 13.1/12 ≈ 1.0917
# avg_wait_min を baseline=1.0 相当とみなすための割り戻し基準値。
# TIME_FACTOR を改修した場合はこの値も再計算が必要。
TIME_FACTOR_AVG_EFFECTIVE = 13.1 / 12
```

- [ ] **Step 4: テストを走らせて PASS を確認**

Run: `.venv/bin/pytest tests/test_constants.py -v`
Expected: 全 PASS（既存 8 件 + 新規 2 件 = 10 件 passed）

- [ ] **Step 5: コミット**

```bash
git add src/constants.py tests/test_constants.py
git commit -m "feat: add TIME_FACTOR_FLOOR and TIME_FACTOR_AVG_EFFECTIVE constants"
```

---

## Task 2: `build_snapshot_at` の最小実装（TDD）

**Files:**
- Modify: [src/simulator.py](../../../src/simulator.py)
- Test: [tests/test_simulator.py](../../../tests/test_simulator.py)

仕様の §5 参照。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_simulator.py` の末尾に追加（他のテストは Task 3 で別途更新）:

```python
def test_snapshot_at_basic_signature(sample_attractions):
    """build_snapshot_at(attractions, datetime) が WaitTimeSnapshot を返す。"""
    from src.simulator import build_snapshot_at
    target_dt = datetime(2026, 5, 25, 9, 0)
    snap = build_snapshot_at(sample_attractions, target_dt)

    assert isinstance(snap, WaitTimeSnapshot)
    assert snap.timestamp == target_dt
    assert snap.park == "TDL"
    assert len(snap.data) == len(sample_attractions)
    assert all(e.status == "operating" for e in snap.data)
```

- [ ] **Step 2: テストを走らせて FAIL を確認**

Run: `.venv/bin/pytest tests/test_simulator.py::test_snapshot_at_basic_signature -v`
Expected: `ImportError: cannot import name 'build_snapshot_at'` で FAIL

- [ ] **Step 3: src/simulator.py に `build_snapshot_at` を追加**

`build_opening_snapshot` 関数の **直下** に追加（既存関数はまだ削除しない、Task 8 で削除）:

```python
def build_snapshot_at(
    attractions: list[Attraction],
    target_datetime: datetime,
) -> WaitTimeSnapshot:
    """target_datetime 時点の合成 snapshot を返す。

    各エントリの wait_min は Queue-Times stats の全期間平均 (avg_wait_min) に
    時刻補正 (effective_factor / TIME_FACTOR_AVG_EFFECTIVE) を掛けた値。
    avg_wait_min が null の場合は tier ベースの OPENING_BASE_WAIT_BY_TIER に
    同じ時刻補正を適用。effective_factor は get_time_factor(target_datetime.hour)
    を TIME_FACTOR_FLOOR で下限保護した値。
    """
    effective_factor = max(TIME_FACTOR_FLOOR, get_time_factor(target_datetime.hour))
    multiplier = effective_factor / TIME_FACTOR_AVG_EFFECTIVE
    entries = [
        WaitTimeEntry(
            name=a.name,
            wait_min=round(
                (a.avg_wait_min if a.avg_wait_min is not None
                 else OPENING_BASE_WAIT_BY_TIER[a.popularity_tier])
                * multiplier
            ),
            status="operating",
            queue_times_id=a.queue_times_id,
        )
        for a in attractions
    ]
    return WaitTimeSnapshot(timestamp=target_datetime, park="TDL", data=entries)
```

そして冒頭 import を以下のように更新（既存の `OPENING_BASE_WAIT_BY_TIER` import 行を置換）:

```python
from src.constants import (
    OPENING_BASE_WAIT_BY_TIER,
    TIME_FACTOR_AVG_EFFECTIVE,
    TIME_FACTOR_FLOOR,
    get_time_factor,
)
```

- [ ] **Step 4: テストを走らせて PASS を確認**

Run: `.venv/bin/pytest tests/test_simulator.py::test_snapshot_at_basic_signature -v`
Expected: 1 passed

- [ ] **Step 5: 全テストが壊れていないことを確認**

Run: `.venv/bin/pytest -q`
Expected: 既存 64 + 新規 3 (Task 1 で 2 件 + Task 2 で 1 件) = 67 passed

- [ ] **Step 6: コミット**

```bash
git add src/simulator.py tests/test_simulator.py
git commit -m "feat: add build_snapshot_at with time-adjusted baseline"
```

---

## Task 3: 既存 `test_opening_snapshot_*` テスト 6 件を新 API に置換

**Files:**
- Modify: [tests/test_simulator.py](../../../tests/test_simulator.py)

既存の 6 件のテスト（`test_opening_snapshot_basic` 〜 `test_opening_snapshot_uses_avg_wait_when_present`）を `build_snapshot_at` ベースに書き換え、期待値を **β 計算式（下限 0.9 つき）** に合わせる。

仕様 §9.1 参照。検算結果:
- 9:00 multiplier = 0.9 / (13.1/12) = 0.8244
- S 級 (avg=None) → 20 × 0.8244 = 16.49 → round = **16**
- A 級 (avg=None) → 15 × 0.8244 = 12.37 → round = **12**
- C 級 (avg=None) → 5 × 0.8244 = 4.12 → round = **4**
- S 級 (avg=42) → 42 × 0.8244 = 34.62 → round = **35**

- [ ] **Step 1: tests/test_simulator.py の冒頭 import 文を更新**

```python
"""シミュレーションモード（合成 snapshot 生成）のテスト。"""
from datetime import datetime

from src.constants import OPENING_BASE_WAIT_BY_TIER
from src.models import Attraction, WaitTimeSnapshot
from src.router import RouteConstraints, generate_route
from src.simulator import build_snapshot_at
```

⚠️ `date`, `time` の import は不要になる。`build_opening_snapshot` の import も削除。

- [ ] **Step 2: 既存 6 件のテストを以下に書き換え**

```python
def test_snapshot_at_basic(sample_attractions):
    """9:00 を渡すと、avg_wait_min null のアトラクションは tier base × 0.8244 で計算される。"""
    snap = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))

    assert isinstance(snap, WaitTimeSnapshot)
    assert all(e.status == "operating" for e in snap.data)
    # multiplier = 0.9 / (13.1/12) = 0.8244
    expected = {
        "S": round(OPENING_BASE_WAIT_BY_TIER["S"] * 0.8244),  # 16
        "A": round(OPENING_BASE_WAIT_BY_TIER["A"] * 0.8244),  # 12
        "B": round(OPENING_BASE_WAIT_BY_TIER["B"] * 0.8244),  # 8
        "C": round(OPENING_BASE_WAIT_BY_TIER["C"] * 0.8244),  # 4
    }
    for entry, attr in zip(snap.data, sample_attractions):
        assert entry.name == attr.name
        assert entry.wait_min == expected[attr.popularity_tier]


def test_snapshot_at_timestamp_preserves_input(sample_attractions):
    """snapshot.timestamp が引数の datetime そのまま保持される。"""
    target_dt = datetime(2026, 5, 25, 11, 30)
    snap = build_snapshot_at(sample_attractions, target_dt)

    assert snap.timestamp == target_dt
    assert snap.park == "TDL"


def test_snapshot_at_count(sample_attractions):
    snap = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))
    assert len(snap.data) == len(sample_attractions)


def test_snapshot_at_determinism(sample_attractions):
    """同じ引数なら同じ結果。"""
    target_dt = datetime(2026, 5, 25, 9, 0)
    snap_a = build_snapshot_at(sample_attractions, target_dt)
    snap_b = build_snapshot_at(sample_attractions, target_dt)
    assert snap_a == snap_b


def test_snapshot_at_empty_attractions():
    target_dt = datetime(2026, 5, 25, 9, 0)
    snap = build_snapshot_at([], target_dt)
    assert isinstance(snap, WaitTimeSnapshot)
    assert snap.data == []
    assert snap.timestamp == target_dt


def test_snapshot_at_uses_avg_wait_when_present():
    """avg_wait_min が設定されていれば、tier フォールバックでなく avg × multiplier を使う。"""
    attractions = [
        Attraction(
            id="with_avg", name="With Avg", scrape_key="W",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="S",
            queue_times_id=9999, avg_wait_min=42,
        ),
        Attraction(
            id="no_avg", name="No Avg", scrape_key="N",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="C",
        ),
    ]
    snap = build_snapshot_at(attractions, datetime(2026, 5, 25, 9, 0))
    by_name = {e.name: e for e in snap.data}
    # 9:00 multiplier = 0.9 / (13.1/12) ≈ 0.8244
    assert by_name["With Avg"].wait_min == round(42 * (0.9 / (13.1 / 12)))  # = 35
    assert by_name["No Avg"].wait_min == round(OPENING_BASE_WAIT_BY_TIER["C"] * (0.9 / (13.1 / 12)))  # = 4
```

そして Task 2 で末尾に追加した `test_snapshot_at_basic_signature` は **削除する**（`test_snapshot_at_basic` でカバーされるため重複）。

- [ ] **Step 3: テスト実行で全 PASS を確認**

Run: `.venv/bin/pytest tests/test_simulator.py -v`
Expected: 6 件 passed（書き換えた既存 6 件）。Task 2 のシグネチャテストは削除済み。

- [ ] **Step 4: 全体テスト**

Run: `.venv/bin/pytest -q`
Expected: 既存 64 - Task 2 で追加した 1 件削除 + Task 1 の 2 件 + Task 3 の 6 件（既存置換、件数同じ） = **66 passed**

- [ ] **Step 5: コミット**

```bash
git add tests/test_simulator.py
git commit -m "test: rewrite simulator tests for build_snapshot_at API"
```

---

## Task 4: 新規テスト 3 件追加（時刻別 / 下限保護 / null フォールバック）

**Files:**
- Modify: [tests/test_simulator.py](../../../tests/test_simulator.py)

仕様 §9.1 の「新規 3 件」を実装。

- [ ] **Step 1: 失敗する 3 件のテストを `tests/test_simulator.py` の末尾に追加**

```python
def test_snapshot_at_morning_vs_peak(sample_attractions):
    """9:00（朝係数 0.7→下限 0.9）と 11:00（ピーク 1.3）で同じアトラクションの wait_min が異なる。"""
    morning = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 9, 0))
    peak = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 11, 0))

    # avg=None のアトラクションでも、tier base × multiplier の差が出るはず
    by_name_morning = {e.name: e.wait_min for e in morning.data}
    by_name_peak = {e.name: e.wait_min for e in peak.data}
    for name in by_name_morning:
        # 11:00 は 9:00 の (1.3/0.9) ≈ 1.44 倍
        assert by_name_peak[name] > by_name_morning[name]


def test_snapshot_at_floor_protection(sample_attractions):
    """営業時間外（早朝 / 閉園後）でも factor が 0.9 下限を割らない。"""
    # 03:00 と 22:00 — どちらも factor が 0.7 だが下限 0.9 で持ち上がる
    early = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 3, 0))
    late = build_snapshot_at(sample_attractions, datetime(2026, 5, 25, 22, 0))

    # 22:00 と 03:00 は同じ multiplier (0.9/(13.1/12)) になるはず
    early_by_name = {e.name: e.wait_min for e in early.data}
    late_by_name = {e.name: e.wait_min for e in late.data}
    for name in early_by_name:
        assert early_by_name[name] == late_by_name[name]

    # 値が tier base × 0.8244 になっていることを 1 件で確認
    pooh = next(e for e in early.data if e.name == "プーさんのハニーハント")
    # S 級 tier base = 20、0.9/(13.1/12) ≈ 0.8244 → round = 16
    assert pooh.wait_min == round(OPENING_BASE_WAIT_BY_TIER["S"] * (0.9 / (13.1 / 12)))


def test_snapshot_at_avg_null_uses_tier_base_with_multiplier():
    """avg_wait_min=None のアトラクションは tier base × multiplier で計算される（ただ tier base 直接ではない）。"""
    attractions = [
        Attraction(
            id="s_no_avg", name="S No Avg", scrape_key="S",
            area="X", lat=35.633, lng=139.881,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            popularity_tier="S",
        ),
    ]
    # 11:00（ピーク 1.3）でテスト
    snap = build_snapshot_at(attractions, datetime(2026, 5, 25, 11, 0))
    # multiplier = 1.3 / (13.1/12) ≈ 1.1908
    # 20 × 1.1908 = 23.82 → round = 24
    assert snap.data[0].wait_min == round(OPENING_BASE_WAIT_BY_TIER["S"] * (1.3 / (13.1 / 12)))
```

- [ ] **Step 2: テストを走らせて PASS を確認**

Run: `.venv/bin/pytest tests/test_simulator.py -v`
Expected: 既存 6 件 + 新規 3 件 = **9 passed**

- [ ] **Step 3: 全体テスト**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**（Task 3 までの 66 + Task 4 で 3）

- [ ] **Step 4: コミット**

```bash
git add tests/test_simulator.py
git commit -m "test: add time-of-day variation, floor protection, and null fallback tests"
```

---

## Task 5: `test_simulate_then_route` を任意時刻スタート版に更新

**Files:**
- Modify: [tests/test_simulator.py](../../../tests/test_simulator.py)

既存の `test_simulate_then_route` を 11:00 スタートで動かす版に書き換える。

- [ ] **Step 1: 既存の `test_simulate_then_route` を以下に書き換え**

`tests/test_simulator.py` の `test_simulate_then_route` 関数を以下に置換:

```python
def test_simulate_then_route_at_arbitrary_time(sample_attractions):
    """build_snapshot_at で 11:00 スタートの sim を作り、router に流して動くことを確認。"""
    target_dt = datetime(2026, 5, 25, 11, 0)
    snap = build_snapshot_at(sample_attractions, target_dt)
    constraints = RouteConstraints(
        start_time=target_dt,
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[],
    )
    result = generate_route(
        snapshot=snap,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    # 11:00 スタートでも pooh と big_thunder は訪問できる
    visited = [s.id for s in result.steps if s.type == "attraction"]
    assert "pooh" in visited
    assert "big_thunder" in visited
    # 最初の step は 11:00 以降に開始
    if result.steps:
        first_step = result.steps[0]
        assert first_step.arrive >= target_dt
```

- [ ] **Step 2: テスト実行**

Run: `.venv/bin/pytest tests/test_simulator.py::test_simulate_then_route_at_arbitrary_time -v`
Expected: 1 passed

- [ ] **Step 3: 全体テスト**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**（Task 4 と同数。書き換えなので件数変わらず）

- [ ] **Step 4: コミット**

```bash
git add tests/test_simulator.py
git commit -m "test: rewrite simulate-then-route integration with arbitrary start time"
```

---

## Task 6: [app.py](../../../app.py) の import と `build_opening_snapshot` 呼び出しを置換

**Files:**
- Modify: [app.py](../../../app.py)

このタスクでは **UI は変更しない**。`build_opening_snapshot(attractions, sim_date)` を `build_snapshot_at(attractions, datetime.combine(route_date, current_time_val))` に置換するだけ。sim mode では `current_time_val = time(9, 0)` のままなので、挙動は現状と同じ（9:00 baseline、ただし wait_min は β 補正後の値）。

- [ ] **Step 1: import 文の更新**

[app.py:15](../../../app.py:15) を以下に変更:

```python
# 旧
from src.simulator import build_opening_snapshot
# 新
from src.simulator import build_snapshot_at
```

- [ ] **Step 2: line 429 付近の呼び出しを置換**

```python
# 旧
if is_sim_mode:
    snap = build_opening_snapshot(attractions, sim_date)
# 新
if is_sim_mode:
    snap = build_snapshot_at(
        attractions,
        datetime.combine(route_date, current_time_val),
    )
```

- [ ] **Step 3: line 461 付近の fallback 呼び出しを置換**

```python
# 旧
fallback = build_opening_snapshot(attractions, route_date)
# 新
fallback = build_snapshot_at(
    attractions,
    datetime.combine(route_date, current_time_val),
)
```

- [ ] **Step 4: grep で `build_opening_snapshot` 呼び出しが app.py に残ってないことを確認**

Run: `grep -n "build_opening_snapshot" app.py`
Expected: 何も出ない

- [ ] **Step 5: pytest 全体回帰確認**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**

- [ ] **Step 6: Streamlit 起動確認**

⚠️ 既存 streamlit プロセス（PID 2206、port 8501）が稼働中の可能性あり。**ポート 8502 を使う**:

```bash
.venv/bin/streamlit run app.py --server.headless true --server.port 8502 &
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8502
kill %1
```
Expected: `HTTP 200`

- [ ] **Step 7: コミット**

```bash
git add app.py
git commit -m "refactor: switch app.py to build_snapshot_at (UI unchanged)"
```

---

## Task 7a: [app.py](../../../app.py) - sim mode で「現在時刻 / 現在位置」UI を開放 + 警告ロジック拡張

**Files:**
- Modify: [app.py](../../../app.py)

仕様 §6.1, §6.3 参照。

- [ ] **Step 1: [app.py:173-203](../../../app.py:173) の `if not is_sim_mode:` ブロックを以下に書き換え**

```python
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
```

⚠️ 旧コードの `else: current_time_val = time(9, 0); current_loc_id = "エントランス"` ブロックは **完全削除**。

- [ ] **Step 2: [app.py:206](../../../app.py:206) の閉園時刻警告を拡張**

`if not is_sim_mode and current_time_val >= time(21, 0):` 行を以下に書き換え:

```python
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
```

- [ ] **Step 3: pytest 回帰確認**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**

- [ ] **Step 4: Streamlit 起動 + 目視確認手順**

```bash
.venv/bin/streamlit run app.py --server.headless true --server.port 8502 &
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8502
kill %1
```
Expected: `HTTP 200`

東郷さん側の目視確認チェックリスト（**ブラウザで http://localhost:8502 を開いて**）:
- [ ] sim モード選択 → 「現在時刻」「現在位置」フィールドが表示される
- [ ] sim モードの「現在時刻」初期値が `09:00`
- [ ] sim モードで「⟳ いま」ボタンが **表示されない**
- [ ] 当日モードで「⟳ いま」ボタンが **表示される**（既存挙動）
- [ ] sim モードで「現在時刻」を `22:00` に変更 → 閉園警告が出る
- [ ] sim モードで「現在時刻」を `08:00` に変更 → 開園前警告が出る（新規）

- [ ] **Step 5: コミット**

```bash
git add app.py
git commit -m "feat: open current-time and current-location to sim mode with warnings"
```

---

## Task 7b: [app.py](../../../app.py) - sim mode で「乗った」UI を開放 + router に visited を渡す

**Files:**
- Modify: [app.py](../../../app.py)

仕様 §6.2 参照。

- [ ] **Step 1: [app.py:218-224](../../../app.py:218) の「乗った」表示分岐を削除**

`with st.expander("▼ アトラクション設定", expanded=False):` ブロック内の for ループ冒頭を以下に書き換え:

```python
# 旧
for a in sorted(attractions, key=lambda x: (x.area, x.name)):
    if is_sim_mode:
        col_must, col_prio = st.columns([1, 3])
        col_done = None
    else:
        col_must, col_done, col_prio = st.columns([1, 1, 3])
```

```python
# 新（sim/live 共通の 3 カラム）
for a in sorted(attractions, key=lambda x: (x.area, x.name)):
    col_must, col_done, col_prio = st.columns([1, 1, 3])
```

そして以下の `if col_done is not None:` の **条件分岐を削除**（直接 `with col_done:` に変更）:

```python
# 旧
if col_done is not None:
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
```

```python
# 新（無条件で「乗った」を表示・処理）
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
```

- [ ] **Step 2: [app.py:527-529](../../../app.py:527) の router 呼び出しで visited を sim でも渡すように修正**

```python
# 旧
visited=(
    set(st.session_state.visited_attractions)
    if not is_sim_mode else None
),
```

```python
# 新（sim でも visited を渡す）
visited=set(st.session_state.visited_attractions),
```

- [ ] **Step 3: pytest 回帰確認**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**

- [ ] **Step 4: Streamlit 起動 + 目視確認**

```bash
.venv/bin/streamlit run app.py --server.headless true --server.port 8502 &
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8502
kill %1
```
Expected: `HTTP 200`

東郷さん側の目視確認:
- [ ] sim モード → アトラクション設定 expander を開く → 各行に「必ず乗る / 乗った / 優先度」の 3 カラムが表示
- [ ] sim モードで「乗った」を pooh と big_thunder にチェック → ルート生成 → ルートに pooh / big_thunder が含まれない
- [ ] sim モードで sim_date を 5/25 / 現在時刻 11:00 / 現在位置「シンデレラ城前」（attraction id）にして「合成 snapshot 生成」 → 11:00 から始まるルートが生成

- [ ] **Step 5: コミット**

```bash
git add app.py
git commit -m "feat: open done-checkbox to sim mode and pass visited to router"
```

---

## Task 8: `build_opening_snapshot` を [src/simulator.py](../../../src/simulator.py) から削除

**Files:**
- Modify: [src/simulator.py](../../../src/simulator.py)

仕様 §13 DoD: 「`grep -rn build_opening_snapshot` で 0 件」。

- [ ] **Step 1: src/simulator.py から `build_opening_snapshot` 関数を削除**

[src/simulator.py:15-39](../../../src/simulator.py:15) の `build_opening_snapshot` 関数定義を完全削除。`build_snapshot_at` のみ残す。

ファイル全体は概ね以下のような構造になる:

```python
"""シミュレーションモード用の合成 WaitTimeSnapshot 生成。

来園日前のプランニング（叩き台作成）用に、実 API を叩かずに
理論値ベースの snapshot を作る。任意時刻スタートに対応し、合成 snapshot 内の
wait_min は時刻補正（下限 0.9 つき）された値を持つ。
"""
from __future__ import annotations

from datetime import datetime

from src.constants import (
    OPENING_BASE_WAIT_BY_TIER,
    TIME_FACTOR_AVG_EFFECTIVE,
    TIME_FACTOR_FLOOR,
    get_time_factor,
)
from src.models import Attraction, WaitTimeEntry, WaitTimeSnapshot


def build_snapshot_at(
    attractions: list[Attraction],
    target_datetime: datetime,
) -> WaitTimeSnapshot:
    # ... (Task 2 で追加した本体)
```

`from datetime import date, datetime, time` も `datetime` のみに整理する（`date` / `time` は build_opening_snapshot だけで使っていた）。

- [ ] **Step 2: grep で残存呼び出しが 0 件であることを確認**

Run: `grep -rn "build_opening_snapshot" src/ app.py tests/`
Expected: 何も出ない

- [ ] **Step 3: pytest 全体回帰確認**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**

- [ ] **Step 4: コミット**

```bash
git add src/simulator.py
git commit -m "refactor: remove deprecated build_opening_snapshot"
```

---

## Task 9: [PROGRESS.md](../../../PROGRESS.md) / [lessons.md](../../../lessons.md) 更新

**Files:**
- Modify: [PROGRESS.md](../../../PROGRESS.md)
- Modify: [lessons.md](../../../lessons.md)

このタスクで Phase 7 デプロイ前の臨時作業を記録する。

- [ ] **Step 1: PROGRESS.md §1 「現在のステータス」に追記**

§1 の冒頭サマリ（5/22 のコミット表）の **直下** に、5/23 セッションを追加:

```markdown
**5/23 セッション**: シミュレーションモードの時刻軸拡張を実装（Phase 7 デプロイ前の追加機能、東郷さん要求）。
任意時刻スタート + 「現在時刻 / 現在位置 / 乗った」UI を sim でも開放、wait_min は β 計算式（下限 0.9）で時刻補正。
詳細は [docs/superpowers/specs/2026-05-23-sim-time-axis-design.md](docs/superpowers/specs/2026-05-23-sim-time-axis-design.md) と plans/2026-05-23-sim-time-axis.md。
テスト 64 → 69 PASS。次は Phase 7（デプロイ）。
```

- [ ] **Step 2: PROGRESS.md §3 「次にやること」セクションの A. を更新**

§3 A の Phase 7 タスク説明の上部に注記を追加:

```markdown
**前提**: 5/23 中に「シミュ時刻軸拡張」が完了済（[plans/2026-05-23-sim-time-axis.md](docs/superpowers/plans/2026-05-23-sim-time-axis.md)）。
このタスクはその次のステップとして実施。
```

- [ ] **Step 3: lessons.md #18 に追記**

`### 18. 役割重複の解消は「機能を削る」より「別モードを足す」方が筋がいい` のセクション末尾（学びの段落の後ろ）に、新しい段落を追加:

```markdown
**追記（2026-05-23）**: ただし、シミュレーションモードを「任意時刻スタート + 現在位置 / 乗った」に
拡張した結果、当日モードと役割が重なる場面が出てきた。このときは「役割を分けるために sim を制限する」より
**「役割重複を allow して UI コード分岐を削減する」** 方が正解だった（is_sim_mode 分岐がアトラクション設定で
2 段、現在時刻入力で 1 段、合計 3 段削れた）。役割が後から重なってきた場合は、シンプル化の方向に倒す
判断もある。原則: 機能追加時には「別モードで分ける」、機能成熟後に「重複が見えたら統合」のサイクル。
```

- [ ] **Step 4: 最終 pytest 確認**

Run: `.venv/bin/pytest -q`
Expected: **69 passed**

- [ ] **Step 5: コミット**

```bash
git add PROGRESS.md lessons.md
git commit -m "docs: record sim time-axis implementation in PROGRESS / lessons"
```

---

## 完了の DoD（Definition of Done）

仕様 §13 の DoD と一致:

- [ ] `.venv/bin/pytest -q` で **69 passed**
- [ ] `grep -rn "build_opening_snapshot" .` で `docs/` 配下の参照のみ（コード側に残骸ゼロ）
- [ ] sim モードで「現在時刻 / 現在位置 / 乗った」が表示され入力できる
- [ ] sim モードで `現在時刻 = 11:30` に設定 → ルート生成 → **11:30 以降から始まるルート** が生成
- [ ] sim モードで美女と野獣の wait_min が時刻によって変わる（9:00 = 16, 11:00 = 24, ※avg なしの場合の値、avg=74 が入れば 9:00 = 61, 11:00 = 88）
- [ ] 営業時間外（3:00 / 22:00）でも snapshot が下限 0.9 で生成
- [ ] PROGRESS.md / lessons.md が更新済
- [ ] `git status` クリーン、`git log --oneline -10` に Task 1-9 の 9 コミットが見える

---

## タスク一覧（俯瞰）

| Task | 主担当 | 所要 | 検証 |
|---|---|---|---|
| 1. constants 拡張 | TDD | 5 分 | pytest |
| 2. build_snapshot_at 実装 | TDD | 10 分 | pytest |
| 3. 既存テスト 6 件更新 | Refactor | 15 分 | pytest |
| 4. 新規テスト 3 件追加 | TDD | 15 分 | pytest |
| 5. 統合テスト更新 | Refactor | 10 分 | pytest |
| 6. app.py - 呼び出し置換 | Refactor | 10 分 | pytest + Streamlit 起動 |
| 7a. UI - 現在時刻/位置/警告 | Feature | 15 分 | 東郷さん目視 |
| 7b. UI - 乗った + visited | Feature | 15 分 | 東郷さん目視 |
| 8. build_opening_snapshot 削除 | Cleanup | 5 分 | grep + pytest |
| 9. docs 更新 | Docs | 10 分 | git diff |

**総計: 約 110 分（1 時間 50 分）** — 仕様書 §10.2 で見積もった「3〜5 時間」内に収まる見込み。

---

## 参照

- [仕様書](../specs/2026-05-23-sim-time-axis-design.md)
- [Phase 7 デプロイプラン](2026-05-23-phase-7-deployment.md)
- [進捗ハンドオフ](../../../PROGRESS.md)
- [プロジェクト指示](../../../CLAUDE.md)
- [教訓集](../../../lessons.md)
