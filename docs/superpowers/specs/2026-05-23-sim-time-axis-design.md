# シミュレーションモード時刻軸拡張 — 設計仕様

**作成日**: 2026-05-23
**対象バージョン**: v1（Phase 7 デプロイ前に取り込む）
**関連プロジェクト指示**: [CLAUDE.md](../../../CLAUDE.md)
**実装計画**: （writing-plans フェーズで作成予定）

---

## 1. 背景・動機

### 1.1 現状の制約

[src/simulator.py](../../../src/simulator.py) の `build_opening_snapshot(attractions, target_date)` は **常に 9:00 開園時刻の合成 snapshot** を返す。これに伴って [app.py](../../../app.py) のシミュレーションモード UI は以下の固定値を持つ:

- `current_time_val = time(9, 0)` （[app.py:202](../../../app.py:202)）
- `current_loc_id = "エントランス"` （[app.py:203](../../../app.py:203)）
- 「現在時刻」「現在位置」「乗った」UI は当日モードのみ表示（[app.py:175](../../../app.py:175) `if not is_sim_mode:`）

この構造は「**sim = 前日叩き台 / 当日 = リアル運用**」の役割分担を前提とする（[lessons #18](../../../lessons.md)）。

### 1.2 動機

東郷さん要求（2026-05-23 セッション）:

> シミュレーションモードにも時間の概念を入れたい。合成 Snapshot 生成に時刻別の予想取得を入れたいです。また、ルート生成時も任意の時刻基準で生成したいです。

**動機の本質**: 時刻別の混雑ピークを考慮した予測精度向上。例えば 11:00 入園シナリオで「ピーク時の待ち時間 90 分」を baseline にしたシミュレーションをしたい。9:00 固定では現実とのギャップが大きい。

---

## 2. スコープと範囲

### 2.1 In Scope

- 任意時刻 T で合成 snapshot を作れるようにする
- sim モードで「現在時刻」「現在位置」「乗った」UI を開放（当日モードと同等）
- 合成 snapshot の wait_min を時刻別に補正（計算式 β、§3 で詳述）

### 2.2 Out of Scope

- TIME_FACTOR の全面再設計（factor 値そのものは現状維持、下限保護のみ追加）
- Queue-Times の時刻別 stats 取り込み（v2 候補。今回は avg_wait_min から逆算するアプローチ）
- 当日モードの仕様変更（無触り）
- predictor の計算ロジック変更（snapshot.timestamp が変わることで自動的に時刻補正が効く）

### 2.3 役割定義の変更

| 観点 | 旧 | 新 |
|---|---|---|
| sim モード | 9:00 固定 / エントランス固定 / 「乗った」非表示 = **前日叩き台専用** | 任意時刻 / 任意位置 / 「乗った」入力可 = **合成データ版の当日モード** |
| 当日モード | 任意時刻 / 任意位置 / 「乗った」あり | （変化なし） |
| 両モードの差分 | UI 入力項目 + データソース | **データソース（Queue-Times 実 API or 合成 snapshot）のみ** |

→ [lessons #18](../../../lessons.md)「役割重複は別モード追加で済むことが多い」とは逆方向の判断になる。今回は **役割重複を allow して UI コード分岐を削減** する。lessons #18 への追記は実装時に行う（「ただし役割が後で重なってきた場合は、削除より重複を allow した方が良い」）。

---

## 3. 計算式（β 案 = 下限 0.9）

### 3.1 定数定義

[src/constants.py](../../../src/constants.py) に追加:

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

### 3.2 計算式

```
effective_factor(T) = max(TIME_FACTOR_FLOOR, get_time_factor(T.hour))
wait_min_at_T = baseline × effective_factor(T) / TIME_FACTOR_AVG_EFFECTIVE
```

ここで `baseline` は:
- `attraction.avg_wait_min`（Queue-Times all-time average）が non-null なら、その値
- null なら `OPENING_BASE_WAIT_BY_TIER[attraction.popularity_tier]`（既存定数）

### 3.3 検算（美女と野獣 avg=74、C 級 avg=15）

| T.hour | factor | effective | multiplier | 美女と野獣 wait | C 級 wait |
|---|---|---|---|---|---|
| 9 | 0.7 | 0.9 | 0.8244 | 61 | 12 |
| 11 | 1.3 | 1.3 | 1.1908 | 88 | 18 |
| 13 | 1.3 | 1.3 | 1.1908 | 88 | 18 |
| 15 | 1.2 | 1.2 | 1.0992 | 81 | 16 |
| 18 | 1.0 | 1.0 | 0.9160 | 68 | 14 |
| 20 | 0.7 | 0.9 | 0.8244 | 61 | 12 |

### 3.4 副作用の明示

現状 sim mode（9:00 開園想定の合成 snapshot）の wait_min も変わる:
- 美女と野獣: **74 → 61 分**（17% 減）
- C 級アトラクション: **15 → 12 分**（20% 減）

これは「朝開園直後は実際少し空いている」を反映する仕様変更。シミュ結果が前回より楽観的に出る可能性があるが、5/24 リハで Queue-Times 実値と比較して微調整余地を残す（§9 リスク参照）。

---

## 4. ファイル変更点

| ファイル | 変更種別 | 概要 |
|---|---|---|
| [src/constants.py](../../../src/constants.py) | 追加 | `TIME_FACTOR_FLOOR = 0.9` と `TIME_FACTOR_AVG_EFFECTIVE = 1.09` |
| [src/simulator.py](../../../src/simulator.py) | 置換 | `build_opening_snapshot(attractions, target_date)` を削除し、`build_snapshot_at(attractions, target_datetime)` を新規実装 |
| [app.py](../../../app.py) | 修正 | sim mode の固定値削除、UI 分岐削減、`build_snapshot_at` 呼び出しに変更 |
| [tests/test_simulator.py](../../../tests/test_simulator.py) | 更新 + 追加 | 既存 5 件を新 API に置換 + 3 件追加（時刻別 / 下限保護 / null フォールバック） |
| [tests/test_router.py](../../../tests/test_router.py) | 更新 | `test_simulate_then_route` を任意時刻スタート版に変更 |
| [PROGRESS.md](../../../PROGRESS.md) | 更新 | Phase 7 着手前の臨時タスクとして追記 |
| [lessons.md](../../../lessons.md) | 更新 | lessons #18 に追記（役割重複を allow するケースもある）|

---

## 5. `build_snapshot_at` の実装仕様

```python
def build_snapshot_at(
    attractions: list[Attraction],
    target_datetime: datetime,
) -> WaitTimeSnapshot:
    """target_datetime 時点の合成 snapshot を返す。

    各エントリの wait_min は Queue-Times stats の全期間平均 (avg_wait_min) に
    時刻補正 (effective_factor / TIME_FACTOR_AVG_EFFECTIVE) を掛けた値。
    avg_wait_min が null の場合は tier ベースの OPENING_BASE_WAIT_BY_TIER に
    同じ時刻補正を適用。

    effective_factor は get_time_factor(target_datetime.hour) を TIME_FACTOR_FLOOR
    で下限保護した値。営業時間外の極端な値（早朝・閉園後）も下限 0.9 で安定。
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

設計上のポイント:
- `round()` で int に丸める（`WaitTimeEntry.wait_min` は `int` 型）
- avg_wait_min が null のときも multiplier を掛ける（tier base にも時刻補正を適用 = 統一感）
- snapshot.timestamp は target_datetime そのまま（時刻情報を保持）

---

## 6. app.py の変更箇所

### 6.1 sim mode UI 開放（[app.py:173-203](../../../app.py:173) を改修）

旧:
```python
if not is_sim_mode:
    col_now, col_loc = st.columns(2)
    # 「現在時刻」「⟳ いま」「現在位置」UI
else:
    current_time_val = time(9, 0)
    current_loc_id = "エントランス"
```

新:
```python
# モードを問わず「現在時刻」「現在位置」を表示
col_now, col_loc = st.columns(2)
with col_now:
    # sim モードのデフォルトは 9:00、当日モードは datetime.now()
    default_time = time(9, 0) if is_sim_mode else datetime.now().time().replace(second=0, microsecond=0)
    now_token = st.session_state.get("now_token", 0)
    current_time_val = st.time_input(
        "現在時刻",
        value=default_time,
        key=f"current_time_{token}_{now_token}",
    )
    # 「⟳ いま」ボタンは当日モードのみ（sim では現在時刻に戻す意味がない）
    if not is_sim_mode:
        if st.button("⟳ いま", key=f"btn_now_{token}", help="..."):
            st.session_state.now_token = now_token + 1
            st.rerun()
with col_loc:
    # 当日モードと同じく、エントランス + 全アトラクションから選択
    loc_options = ["エントランス"] + [a.id for a in attractions]
    current_loc_id = st.selectbox(
        "現在位置",
        loc_options,
        format_func=lambda x: ("エントランス" if x == "エントランス" else attraction_map[x].name),
        key=f"current_loc_{token}",
    )
```

### 6.2 「乗った」UI 開放（[app.py:218-224](../../../app.py:218) を改修）

旧:
```python
for a in sorted(attractions, key=lambda x: (x.area, x.name)):
    if is_sim_mode:
        col_must, col_prio = st.columns([1, 3])
        col_done = None
    else:
        col_must, col_done, col_prio = st.columns([1, 1, 3])
```

新（モードを問わず 3 カラム）:
```python
for a in sorted(attractions, key=lambda x: (x.area, x.name)):
    col_must, col_done, col_prio = st.columns([1, 1, 3])
```

### 6.3 閉園警告を sim にも適用（[app.py:206](../../../app.py:206)）

旧:
```python
if not is_sim_mode and current_time_val >= time(21, 0):
    st.warning("⚠️ 現在時刻が閉園時刻（21:00）を過ぎています。...")
```

新:
```python
if current_time_val >= time(21, 0):
    st.warning("⚠️ 現在時刻が閉園時刻（21:00）を過ぎています。...")
elif current_time_val < time(9, 0):
    st.warning("⚠️ 開園時刻（9:00）前が指定されています。ルートは開園後から計算されます。")
```

### 6.4 `build_opening_snapshot` 呼び出しを置換（[app.py:429](../../../app.py:429), [app.py:461](../../../app.py:461)）

旧:
```python
snap = build_opening_snapshot(attractions, sim_date)
# ...
fallback = build_opening_snapshot(attractions, route_date)
```

新:
```python
target_dt = datetime.combine(route_date, current_time_val)
snap = build_snapshot_at(attractions, target_dt)
# ...
fallback = build_snapshot_at(attractions, target_dt)
```

### 6.5 import 文の更新

```python
# 旧
from src.simulator import build_opening_snapshot
# 新
from src.simulator import build_snapshot_at
```

---

## 7. データフロー

```
[UI sim mode]
  日付選択:    2026-05-25
  現在時刻:    11:30        ← sim でも入力可
  現在位置:    シンデレラ城前 ← sim でも入力可
  乗った:      {pooh, monster} ← sim でも入力可
       ↓
[app.py]
  target_dt = datetime.combine(2026-05-25, 11:30)
  current_loc = attraction_map[current_loc_id].coords or entrance
  visited = {pooh, monster}
       ↓
[build_snapshot_at(attractions, target_dt)]
  effective_factor = max(0.9, get_time_factor(11)) = 1.3
  multiplier = 1.3 / 1.09 = 1.193
  for each attraction:
    wait_min = round(74 * 1.193) = 88   # 美女と野獣
    wait_min = round(15 * 1.193) = 18   # C 級
  snapshot.timestamp = target_dt
       ↓
[generate_route(snapshot, ..., constraints={
    start_time=target_dt, entrance=current_loc, fixed_blocks=[...]
  }, visited=visited)]
       ↓
[RouteResult]  ← 11:30 開始のルートが返る
```

---

## 8. エラーハンドリング

| ケース | 挙動 |
|---|---|
| `target_datetime` が 9:00 未満 | UI 側で「⚠️ 開園時刻前」警告を新規表示。snapshot は下限 0.9 で生成可、router は current_time < close_time で動く |
| `target_datetime` が 21:00 以上 | UI 側で既存の閉園警告を sim でも表示（現状は当日モードのみ。`not is_sim_mode` 条件を削除） |
| `avg_wait_min` が null（minnie_style 1 件） | tier base × multiplier でフォールバック（§5 実装でカバー済） |
| sim 中に「乗った」に存在しない id（マスタ削除等） | 既存の localStorage zombie 対策（[lessons #27](../../../lessons.md)）が効く（valid_attraction_ids フィルタ） |
| target_datetime が極端に過去/未来（営業時間外、例 03:00） | `get_time_factor()` が defensive ガード（hour<9 で 0.7、hour>=21 で 0.7）→ 下限保護で 0.9 に持ち上がる。snapshot は作れる |

---

## 9. テスト方針

### 9.1 `tests/test_simulator.py`（既存 5 件更新 + 3 件追加 = 計 8 件）

| テスト | 内容 | 期待値 |
|---|---|---|
| 既存: `test_build_opening_snapshot_has_all_attractions` | リネーム & 引数を `datetime(..., 9, 0)` に変更 | snapshot.data が 21 件 |
| 既存: `test_build_opening_snapshot_timestamp` | 同上 | snapshot.timestamp == target_datetime |
| 既存: `test_build_opening_snapshot_uses_avg_wait_min` | 9:00 で美女と野獣の wait_min を新計算式で再計算 | 61 分（旧: 74） |
| 既存: `test_build_opening_snapshot_fallback_for_null_avg` | 9:00 で avg=null の S 級が 16 分（旧: 20 分） | 16 分 |
| 既存: `test_build_opening_snapshot_status_operating` | 同上 | 全 entry.status == "operating" |
| 新規: `test_snapshot_at_morning_vs_peak` | 9:00 と 11:00 で同じアトラクションの wait_min が異なる | 9:00 < 11:00 (例: 61 < 88) |
| 新規: `test_snapshot_at_floor_protection` | 22:00 や 3:00（営業時間外）でも factor が 0.9 下限を割らない | 0.9/1.09 ≒ 0.826 の multiplier 適用 |
| 新規: `test_snapshot_at_avg_null_uses_tier_base_with_multiplier` | avg_wait_min=None の S 級が 11:00 で 24 分（20 × 1.193） | 24 分 |

### 9.2 `tests/test_router.py` 統合テスト

| テスト | 内容 |
|---|---|
| 更新: `test_simulate_then_route` | `build_snapshot_at(attractions, datetime(2026, 5, 25, 11, 0))` で sim+route が動くことを確認。start_time=11:00 でルートが生成される |

### 9.3 期待されるテスト数の遷移

現状 64 → **67**（3 件追加、5 件は置換）。

### 9.4 統合テスト戦略

- pytest 全テスト PASS を CI の代替として実行
- Streamlit UI は東郷さん側で目視確認（5/23 セッション中 + 5/24 リハ）
- 5/24 リハで Queue-Times 実値と sim 予測値の **diff を取って大外し検証**（例: 同時刻の美女と野獣で sim 88 分 vs 実値 120 分 → 32 分のズレなら許容、80 分ズレなら計算式再検討）

---

## 10. Phase 7 デプロイへの影響

### 10.1 タスク順序の変更

旧プラン（[2026-05-23-phase-7-deployment.md](../plans/2026-05-23-phase-7-deployment.md)）:
1. Task 26: requirements.txt + README
2. Task 27: GitHub + Streamlit Cloud デプロイ
3. Task 28: 動作確認

新プラン:
0. **本仕様の実装（writing-plans で作成予定）** ← 5/23 中に完了させる
1. Task 26: requirements.txt + README
2. Task 27: GitHub + Streamlit Cloud デプロイ
3. Task 28: 動作確認 + **sim mode の任意時刻スタートをデプロイ環境で確認**

### 10.2 工数見積もりへの影響

本仕様の実装工数: **3〜5 時間**（テスト含む）
Phase 7 全体工数（旧）: 2〜3.5 時間
新合計: **5〜8.5 時間**

→ 5/23 中に実装 + Task 26-27 を終え、5/24 に Task 28 + リハという日程は維持可能。

---

## 11. リスクと対策

| リスク | 確率 | 影響 | 対策 |
|---|---|---|---|
| 計算式 β の下限 0.9 が現実と合わない | 中 | 中 | 5/24 リハで Queue-Times 実値と diff を取り、必要なら下限値 (0.9 → 0.85 / 1.0) を微調整 |
| シミュ結果が前回より楽観的になり東郷さんが違和感を持つ | 中 | 低 | 仕様書 §3.4 で副作用を明示済。リハで「シミュ vs 実値」を並べて確認 |
| UI 開放で sim モードの localStorage に zombie データ混入 | 低 | 低 | 既存の valid_attraction_ids フィルタ（[lessons #27](../../../lessons.md)）でカバー |
| 「⟳ いま」ボタンを sim から消すと当日モード→sim 切替時に UI 差分が出る | 低 | 低 | モード切替時に route+snapshot をクリアする既存処理（[5/22 commit ea5f37f](../../../PROGRESS.md)）で連動済 |
| `TIME_FACTOR_AVG_EFFECTIVE = 1.09` がハードコード値で TIME_FACTOR の見直しと整合性が崩れる | 低 | 低 | constants.py 内で計算式コメントを明示。TIME_FACTOR 改修時は同時更新が必要と明示 |

---

## 12. 関連ドキュメント

- [プロジェクト指示](../../../CLAUDE.md)
- [メイン仕様書](2026-05-16-tdl-route-planner-design.md)
- [Phase 7 デプロイプラン](../plans/2026-05-23-phase-7-deployment.md)
- [進捗ハンドオフ](../../../PROGRESS.md)
- [教訓集](../../../lessons.md)（特に #18 役割重複、#27 localStorage zombie）

---

## 13. 受け入れ基準（DoD）

- [ ] `pytest -q` で **67 passed**
- [ ] `build_opening_snapshot` の呼び出しが repo 内に残っていない（`grep -rn build_opening_snapshot` で 0 件）
- [ ] sim モードで「現在時刻」「現在位置」「乗った」が表示され、入力できる
- [ ] sim モードで現在時刻 = 11:30 に設定 → ルート生成 → 11:30 から始まるルートが生成される
- [ ] sim モードで美女と野獣の wait_min が時刻によって変わる（9:00 = 61 分 / 11:00 = 88 分）
- [ ] 営業時間外（3:00 / 22:00）でも snapshot が下限 0.9 で生成できる
- [ ] PROGRESS.md / lessons.md に実装結果が反映されている
- [ ] git tree がクリーン
