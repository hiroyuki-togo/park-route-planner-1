# TDL Route Planner — 設計仕様書 v1

> 東京ディズニーランド（TDL）来園日に使う、個人ツールとしての終日ルート自動生成アプリ。
> 想定実装環境：Python 3.11+ / Streamlit / Claude Code 併用。
> 来園日：**2026-05-25（月曜）**、特別イベントなしの平日。

| 項目 | 値 |
|---|---|
| 作成日 | 2026-05-16 |
| オーナー | 東郷 |
| ステータス | 設計確定、Phase 1 実装着手前 |
| 関連ファイル | [CLAUDE.md](../../../CLAUDE.md) / [memory.md](../../../memory.md) |
| 前身 | [archive/ディズニープラン-TDS.md](../../../archive/ディズニープラン-TDS.md)（TDS 向け旧版） |

---

## 1. 目的とスコープ

### 1.1 目的

東京ディズニーランド来園日に、リアルタイム待ち時間データを取得し、優先度・食事・ショー・パレード・DPA 予約・天候を加味した **終日ルートを自動生成する** 個人ツールを構築する。

### 1.2 スコープ（v1 で実装する）

- TDL 公式サイト（`/tdl/realtime/attraction/`）からのリアルタイム待ち時間取得
- 終日ルート自動生成（貪欲法 + スコアリング）
- DPA 予約の手動登録とルートへの自動組み込み
- must-visit ハイブリッド優先度（チェックボックス + ★1-5 スライダー）
- パレード対応（fixed_block 化、鑑賞 / 非鑑賞両対応）
- 雨天モード（移動時間 +20%、屋外アトラクション優先度ダウン）
- レストランマスタ + 食事ブロック連携
- 設定の当日内永続化（localStorage、日付キー）
- 未消化 must-visit / DPA 窓ミスの警告表示
- Streamlit Community Cloud へのデプロイ（スマホブラウザアクセス）

### 1.3 スコープ外（v2 以降）

- DPA 購入候補の最適化提案（「どれを買うべきか」）
- 当日履歴の永続蓄積（Streamlit Cloud のコンテナ再起動で消える）
- ランド／シー両対応、複数日対応
- 機械学習による待ち時間予測
- 動的天気取得（OpenWeatherMap API 連携）
- 認証 / 同行者との設定同期（同行者は **URL 共有による閲覧のみ**）

### 1.4 同行者の利用

複数人での来園を想定するが、**ルート設定の編集は東郷さんのみ**。同行者は同じ URL をスマホで開いてルート確認・待ち時間チェックに使う（追加実装ゼロ）。協調的編集は v1 対象外。

---

## 2. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  Streamlit App (app.py)                         │
│   ├─ 優先度・must-visit 設定                    │
│   ├─ 食事・ショー・パレード・DPA 予約入力       │
│   ├─ 雨天モードトグル                           │
│   ├─ 推奨ルート表示                             │
│   └─ localStorage（日付スコープ永続化）         │
│                                                 │
│  Core Modules (src/)                            │
│   ├─ scraper.py     → 公式サイトから待ち時間   │
│   ├─ predictor.py   → 時間帯による待ち時間補正 │
│   ├─ distance.py    → 移動時間 + パレード補正  │
│   ├─ router.py      → 貪欲法でルート生成       │
│   ├─ models.py      → Pydantic モデル定義      │
│   └─ constants.py   → 開園時間 / 係数 / 定数   │
│                                                 │
│  Data (data/)                                   │
│   ├─ attractions.json  : マスタ                │
│   ├─ restaurants.json  : レストランマスタ      │
│   └─ snapshots/        : 取得履歴（揮発）      │
└─────────────────────────────────────────────────┘
```

---

## 3. データモデル

### 3.1 アトラクションマスタ（`data/attractions.json`）

```json
{
  "park": "TDL",
  "open_time": "09:00",
  "close_time": "21:00",
  "entrance": { "lat": 35.6329, "lng": 139.8804 },
  "attractions": [
    {
      "id": "beauty_and_beast",
      "name": "美女と野獣\"魔法のものがたり\"",
      "scrape_key": "美女と野獣",
      "area": "ファンタジーランド",
      "lat": null,
      "lng": null,
      "experience_time_min": 7,
      "queue_walk_min": 5,
      "default_priority": 5,
      "dpa_eligible": true,
      "requires_reservation": true,
      "outdoor": false,
      "popularity_tier": "S"
    }
  ]
}
```

`lat` / `lng` は Phase 3 のマスタ整備時に Google マップで手動測定して埋める。雛形生成時は `null` で出力する。

**フィールド定義**

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string | 内部識別子。snake_case |
| `scrape_key` | string | 公式サイト表記とのファジーマッチ用キー |
| `area` | string | エリア名（TDL 7エリアのいずれか） |
| `lat`, `lng` | float | 待機列入口の緯度経度（Googleマップで手動測定） |
| `experience_time_min` | int | 乗車・体験時間 |
| `default_priority` | int (1-5) | UI 初期値 |
| `dpa_eligible` | bool | プレミアアクセス対象か |
| `requires_reservation` | bool | スタンバイ列のみでは乗れず DPA / スタンバイパス必須か。`true` なら通常候補から除外、DPA 予約で初めてルートに乗る |
| `outdoor` | bool | 屋外アトラクションか。雨天モード時のスコア調整に使用 |
| `popularity_tier` | enum | S / A / B / C |

**エリア一覧（TDL 7エリア）**

```
ワールドバザール、アドベンチャーランド、ウエスタンランド、
クリッターカントリー、ファンタジーランド、トゥーンタウン、トゥモローランド
```

**マスタ整備時の注意（2026-05 時点の現実）**

- スペースマウンテン：閉鎖中（新型は 2027 年予定）→ マスタから除外
- スプラッシュマウンテン：営業終了（2024-06）→ マスタから除外
- 美女と野獣"魔法のものがたり"：`requires_reservation` の最終判定はマスタ整備時に公式サイトで確認

### 3.2 レストランマスタ（`data/restaurants.json`）

主要10店舗程度をカバー：テーブルサービス 5-6 店 + カウンターサービス 4-5 店。軽食ワゴンは省略。

```json
{
  "park": "TDL",
  "restaurants": [
    {
      "id": "blue_bayou",
      "name": "ブルーバイユー・レストラン",
      "area": "アドベンチャーランド",
      "lat": null,
      "lng": null,
      "type": "table_service",
      "ps_available": true,
      "typical_duration_min": 90,
      "open_window": ["11:00", "21:30"]
    }
  ]
}
```

**`type` 別デフォルト所要時間**

| type | 説明 | デフォ所要時間 |
|---|---|---|
| `table_service` | テーブルサービス | 90分 |
| `buffet` | ビュッフェ | 75分 |
| `counter_service` | カウンターサービス | 35分 |

### 3.3 待ち時間スナップショット

```json
{
  "timestamp": "2026-05-25 09:15:00",
  "park": "TDL",
  "data": [
    { "name": "美女と野獣", "wait_min": 90, "status": "operating" },
    { "name": "プーさんのハニーハント", "wait_min": null, "status": "closed" }
  ]
}
```

`status`: `operating` / `closed` / `unknown`

### 3.4 固定ブロック（`FixedBlock`）

```python
class FixedBlock(BaseModel):
    type: Literal["meal", "show", "parade", "dpa"]
    start: datetime
    end: datetime
    label: str                                    # 表示用
    attraction_id: str | None = None              # type="dpa" のとき必須
    restaurant_id: str | None = None              # type="meal" のとき任意
    location: tuple[float, float] | None = None
    watch: bool = False                           # parade のとき：鑑賞するか
```

**type 別の挙動**

| type | location 必須 | 終了後 current_location | 待ち時間扱い |
|---|---|---|---|
| `meal` | 任意（restaurant_id があれば自動） | location があれば更新 | N/A |
| `show` | 任意 | location があれば更新 | N/A |
| `parade` (watch=True) | 必須 | location | N/A |
| `parade` (watch=False) | 不要 | 変化なし。ただし期間中のメインストリート横断移動に +15分ペナルティ |
| `dpa` | 必須（attraction の lat/lng） | attraction の座標 | 15分固定 |

### 3.5 DPA 予約（`DpaReservation`）

UI 入力用の中間モデル。ルータに渡すときに `FixedBlock(type="dpa", ...)` に変換。

```python
class DpaReservation(BaseModel):
    attraction_id: str
    start: time
    end: time
```

### 3.6 ルート出力

```python
class RouteStep(BaseModel):
    type: Literal["attraction", "meal", "show", "parade", "dpa"]
    id: str | None
    arrive: datetime
    ride_start: datetime
    ride_end: datetime
    travel_min: float
    wait_min: float
    via: Literal["standby", "dpa"] | None = None

class RouteResult(BaseModel):
    steps: list[RouteStep]
    unvisited_musts: list[str]
    warnings: list[Warning]

class Warning(BaseModel):
    kind: Literal["time_conflict", "dpa_window_missed", "no_dpa_for_reserved"]
    message: str
    attraction_id: str | None = None
```

---

## 4. データ取得仕様（`src/scraper.py`）

### 4.1 対象エンドポイント

`https://www.tokyodisneyresort.jp/_/realtime/tdl_attraction.json`

公式 TDL リアルタイム待ち時間ページが内部的に叩いている **公開 JSON エンドポイント**（ログイン不要、ブラウザの開発者ツールで誰でも確認可能）。
HTML ページはクライアントサイドレンダリングで JS が JSON を取得して画面を組み立てるため、HTML 直接スクレイピングではデータが取れない。

### 4.2 JSON フィールドマッピング

レスポンスはアトラクション配列。主要フィールド：

| JSON フィールド | 我々のフィールド | 備考 |
|---|---|---|
| `FacilityName` | `name` | フル正式名（例：「美女と野獣"魔法のものがたり"」） |
| `StandbyTime` | `wait_min` | `int` または `null`（null = 待ち時間情報なし） |
| `OperatingStatusCD` | (内部判定用) | `"002"` = 案内終了、その他は実データ |
| `OperatingStatus` | (内部判定用) | テキスト表記の運営状態 |
| `DPAStatusCD` | （v2 で活用） | DPA 販売状況コード |
| `FsStatusCD` | （v2 で活用） | スタンバイパス状況コード |
| `UpdateTime` | （メタ情報） | データ更新時刻（"HH:MM"） |

**`status` 判定ルール**：
- `OperatingStatusCD == "002"`（案内終了）→ `closed`
- `StandbyTime is not None` → `operating`
- それ以外（待ち時間 null かつ 002 でない）→ `unknown`

### 4.3 設計要件

- **アクセス頻度**：5〜10分に1回まで（規約 + 先方負荷の両面）
- **User-Agent**：実在ブラウザ文字列（裸の Python requests ではブロックされる可能性あり）
- **タイムアウト**：30秒
- **リトライ**：3回（指数バックオフ）
- **失敗時**：直近のスナップショットにフォールバック
- **キャッシュ**：同セッション内で前回取得から5分以内なら再取得せず直近値を返す
- **出力**：取得した内部正規化スナップショットを `data/snapshots/{YYYY-MM-DD}_{HHMM}.json` に保存

### 4.4 エッジケース

- JSON 構造変更で抽出失敗 → ログ + 直近スナップショット使用
- アトラクション名表記揺れ → `attractions.json` の `scrape_key` で `difflib.get_close_matches`（閾値 0.6 + 部分一致ボーナス）。JSON は正式名なので揺れは少ないが、マスタ側の短縮表記との照合で必要
- 全アトラクション運営休止 → 空スナップショットを記録、ルータ側で扱う
- API レート制限を受けた場合（HTTP 429 など）→ リトライ後にフォールバック

---

## 5. 待ち時間予測（`src/predictor.py`）

過去データなし、平日・イベントなし前提の単純モデル。

### 5.1 時間帯補正係数（TDL 適用版）

```python
TIME_FACTOR = {
    (9, 10):  0.7,
    (10, 11): 0.9,
    (11, 14): 1.3,
    (14, 17): 1.2,
    (17, 19): 1.0,
    (19, 21): 0.7,
}
```

TDS 用と同係数を流用。**家族連れの多い TDL では昼ピークの偏りが TDS と異なる可能性** あるが、実データなしのため当日検証に委ねる（v2 で調整）。

### 5.2 人気度係数

```python
POPULARITY_FACTOR = { "S": 1.0, "A": 0.9, "B": 0.8, "C": 0.7 }
```

### 5.3 予測式

```python
def predict_wait(attraction, current_wait, current_time, target_time, weather_mode="normal"):
    if target_time - current_time < timedelta(minutes=30):
        return current_wait

    factor_now = get_time_factor(current_time.hour)
    factor_then = get_time_factor(target_time.hour)
    pop_factor = POPULARITY_FACTOR[attraction.popularity_tier]

    delta = (factor_then - factor_now) * pop_factor
    predicted = current_wait * (1 + delta)

    # 雨天モード：屋外アトラクションは予測待ち -30%（来園者減）
    # 屋内アトラクションは一律 +20%（屋外回避組が集中。人気度に依らず一律）
    if weather_mode == "rain":
        if attraction.outdoor:
            predicted *= 0.7
        else:
            predicted *= 1.2

    return max(5, predicted)
```

---

## 6. 距離・移動時間（`src/distance.py`）

### 6.1 基本式

```python
def travel_time_min(loc_a, loc_b, current_time, fixed_blocks, weather_mode="normal"):
    distance_m = geodesic(loc_a, loc_b).meters
    walking_speed = 67  # 4km/h
    park_factor = 1.4

    if weather_mode == "rain":
        park_factor = 1.7   # 傘さし・滑り対策

    base = distance_m / walking_speed * park_factor

    # パレード横断ペナルティ
    if _crosses_main_street(loc_a, loc_b):
        for block in fixed_blocks:
            if block.type == "parade" and not block.watch:
                if block.start <= current_time <= block.end:
                    base += 15
                    break

    return base
```

### 6.2 メインストリート横断判定

`MAIN_STREET_BLOCKING_PAIRS` を静的に定義（実地経験 + Google マップで判断）。城前プラザを通る組み合わせ：

```python
MAIN_STREET_BLOCKING_PAIRS = {
    frozenset(["トゥモローランド", "アドベンチャーランド"]),
    frozenset(["トゥモローランド", "ウエスタンランド"]),
    frozenset(["ファンタジーランド", "アドベンチャーランド"]),
    # Phase 4 で実地経験 + Google マップを見ながら具体ペアを確定する
}
```

水路分断のない TDL では、TDS のような `AREA_MIN_TIME` の必要性は低い。ユークリッド距離 + park_factor + パレード補正で十分。

---

## 7. ルート生成（`src/router.py`）

### 7.1 スコアリング関数

```
Score(候補 i) = (priority[i] × experience_value[i] × weather_value_factor) / (travel + predicted_wait + experience_time)
```

- `experience_value`: S=10, A=7, B=5, C=3
- `priority`: UI 入力 1-5
- `weather_value_factor`: 通常時は 1.0。雨天モード時、屋外アトラクションは 0.7、屋内は 1.0（優先度を下げる）
- 分母：分。`travel` と `predicted_wait` は `weather_mode` 引数を引いて算出（§5.3 / §6.1）

### 7.2 メインループ

```python
def generate_route(snapshot, attractions, constraints, priorities, must_visits, weather_mode="normal"):
    current_time = constraints.start_time
    current_location = constraints.entrance
    blocks = sorted(constraints.fixed_blocks, key=lambda b: b.start)
    route, warnings = [], []
    visited = set()
    must_remaining = set(must_visits)

    while current_time < constraints.close_time:
        # (A) 固定ブロック消化
        if blocks and blocks[0].start <= current_time:
            block = blocks.pop(0)
            step = handle_fixed_block(block, current_time, current_location)
            route.append(step)
            current_time = block.end
            if block.location:
                current_location = block.location
            if block.type == "dpa":
                visited.add(block.attraction_id)
                must_remaining.discard(block.attraction_id)
            continue

        # (B) 次の固定ブロックまでの残り時間
        next_block_start = blocks[0].start if blocks else constraints.close_time
        time_until_block = (next_block_start - current_time).total_seconds() / 60

        # (C) 候補絞り込み（requires_reservation を持つものは除外）
        candidates = [
            a for a in attractions
            if a.id not in visited
            and is_operating(a, snapshot)
            and not a.requires_reservation
        ]
        if not candidates:
            break

        # (D) must-visit が残っていれば優先プール化
        pending_must = [c for c in candidates if c.id in must_remaining]
        pool = pending_must if pending_must else candidates

        # (E) スコアリング
        best, cost = score_and_pick(pool, current_time, current_location, snapshot, priorities, weather_mode)

        # (F) 次の固定ブロックまでに収まらない場合は弾く
        if cost > time_until_block:
            if pending_must:
                warnings.append(time_conflict_warning(best))
                must_remaining.discard(best.id)
                continue
            pool = [c for c in pool if estimated_cost(c, ...) <= time_until_block]
            if not pool:
                current_time = next_block_start
                continue
            best, cost = score_and_pick(pool, ...)

        # (G) ルート追加
        route.append(make_attraction_step(best, current_time, current_location, cost))
        current_time += timedelta(minutes=cost)
        current_location = (best.lat, best.lng)
        visited.add(best.id)
        must_remaining.discard(best.id)

    return RouteResult(steps=route, unvisited_musts=list(must_remaining), warnings=warnings)
```

### 7.3 DPA ブロック処理

```python
def handle_fixed_block(block, current_time, current_location):
    if block.type == "dpa":
        attraction = lookup_attraction(block.attraction_id)
        travel = travel_time_min(current_location, block.location, current_time, [], "normal")
        arrive = current_time + timedelta(minutes=travel)
        if arrive > block.end:
            return warning_step("dpa_window_missed")
        actual_start = max(arrive, block.start)
        wait_min = 15
        return RouteStep(
            type="dpa", id=block.attraction_id,
            arrive=arrive,
            ride_start=actual_start + timedelta(minutes=wait_min),
            ride_end=actual_start + timedelta(minutes=wait_min + attraction.experience_time_min),
            travel_min=travel, wait_min=wait_min, via="dpa",
        )
    elif block.type == "meal":
        # restaurant_id があれば location は既にセット済み
        # label には店名、type="meal" でルート出力
        return RouteStep(type="meal", id=block.restaurant_id, ...)
    elif block.type == "show":
        return RouteStep(type="show", id=None, ...)
    elif block.type == "parade":
        # watch=True なら鑑賞場所で滞在、False なら type="parade" のメモのみ（移動への副作用は distance.py 側）
        return RouteStep(type="parade", id=None, ...)
```

### 7.4 エッジケース

| ケース | 挙動 |
|---|---|
| must-visit に DPA 予約済みの予約必須アトラクション（美女と野獣など） | DPA ブロックで消化、must_remaining から除外 |
| must-visit に DPA 未予約の予約必須アトラクション | 永久に消化されず、`unvisited_musts` に残る + `no_dpa_for_reserved` 警告 |
| DPA 時間窓に間に合わない | `dpa_window_missed` 警告 |
| 全アトラクション運営休止 | 空ルート + 警告 |
| パレード fixed_block 中の移動 | `_crosses_main_street` が true なら +15分 |
| 雨天モード時の屋外アトラクション | predicted_wait は -30%、experience_value は ×0.7 で優先度ダウン |

### 7.5 計算量

- アトラクション数 ≒ 20-25（閉鎖中除外後）
- ステップ数 ≒ 15-20
- 1 ステップあたり O(N) 評価
- 全体：O(N²) ≒ 500 評価。瞬時に完了

---

## 8. UI 仕様（`app.py`、Streamlit）

### 8.1 画面構成

```
┌────────────────────────────────────────────┐
│ 🎢 TDL Route Planner                       │
│ 最終取得: 09:15  [🔄 更新]                  │
│ 📅 2026-05-25（設定は本日中だけ自動保存）   │
├────────────────────────────────────────────┤
│ ☐ 雨天モード                                │
├────────────────────────────────────────────┤
│ ▼ アトラクション設定（折りたたみ可）        │
│  ソアリン                                   │
│   [✓] 必ず乗る  優先度 [★★★★★]           │
│  美女と野獣                                 │
│   [✓] 必ず乗る  優先度 [★★★★★]           │
│   ⚠️ 予約必須：DPA を登録してください       │
│  ...                                        │
├────────────────────────────────────────────┤
│ ▼ 食事ブロック                              │
│  昼食 [ブルーバイユー ▼] 12:00 - [13:30 自動] │
│  夕食 [パン・ギャラクティック ▼] 18:00 - 18:35 │
├────────────────────────────────────────────┤
│ ▼ ショー・パレード                          │
│  [+ 追加]                                   │
│  ☑ Harmony in Color  13:30-14:15  [☑ 鑑賞]  │
│  ☑ Electrical Parade 20:00-20:45  [☐ 鑑賞]  │
├────────────────────────────────────────────┤
│ ▼ DPA 予約                                  │
│  [+ DPA を追加]                             │
│  🎟 美女と野獣  10:30-11:30  [✕]            │
├────────────────────────────────────────────┤
│ [⚡ ルート生成]                              │
├────────────────────────────────────────────┤
│ ▼ 推奨ルート (生成時刻: 09:16)              │
│ 09:15 プーさん     待20分 ⭐⭐⭐⭐⭐        │
│ 10:30 🎟 美女と野獣 (DPA) 待15分            │
│ 12:00 🍴 ブルーバイユー                      │
│ 13:30 ☑ Harmony in Color                    │
│ ...                                          │
│                                              │
│ ⚠️ 未消化の must-visit:                      │
│   - ビッグサンダー（時間内に収まらず）       │
│                                              │
│ [📥 CSV出力] [📋 コピー]                    │
└────────────────────────────────────────────┘
```

### 8.2 状態管理（`st.session_state`）

| キー | 型 | 永続化 | 用途 |
|---|---|---|---|
| `priorities` | `dict[str, int]` | ✅ | アトラクションごとの ★1-5 |
| `must_visits` | `set[str]` | ✅ | 「必ず乗る」チェック済み |
| `meal_blocks` | `list[FixedBlock]` | ✅ | 食事ブロック |
| `show_blocks` | `list[FixedBlock]` | ✅ | ショー・パレードブロック |
| `dpa_blocks` | `list[DpaReservation]` | ✅ | DPA 予約 |
| `weather_mode` | `Literal["normal", "rain"]` | ✅ | 雨天モード |
| `last_snapshot` | `WaitTimeSnapshot` | ❌ | スクレイピング結果 |
| `last_fetch_time` | `datetime` | ❌ | 頻度制限用 |
| `current_route` | `RouteResult` | ❌ | 直近のルート生成結果 |

### 8.3 localStorage 永続化

- ライブラリ：`streamlit-local-storage` または `st.components.v1.html` で JS 直書き
- キー：`tdl_settings_{YYYY-MM-DD}`
- 起動時に当日キーがあれば自動復元、なければ初期状態
- 日付が変わると自動的にクリーンスタート

### 8.4 警告表示

`RouteResult.warnings` と `unvisited_musts` をルート表示下に整理して表示：

```
⚠️ 未消化の must-visit:
  - ビッグサンダー（時間内に収まらず）

⚠️ 警告:
  - DPA「美女と野獣 10:30-11:30」: 直前のルートが長引いた場合、10:50 までに到着できない可能性
```

---

## 9. ディレクトリ構造

```
disney/                              # プロジェクトルート
├── CLAUDE.md
├── memory.md
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-16-tdl-route-planner-design.md  # 本書
├── archive/
│   └── ディズニープラン-TDS.md      # TDS 向け旧版
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── data/
│   ├── attractions.json
│   ├── restaurants.json
│   └── snapshots/                   # 自動生成（揮発）
├── src/
│   ├── __init__.py
│   ├── scraper.py
│   ├── models.py
│   ├── predictor.py
│   ├── distance.py
│   ├── router.py
│   └── constants.py
├── tests/
│   ├── test_scraper.py
│   ├── test_predictor.py
│   ├── test_distance.py
│   ├── test_router.py
│   └── fixtures/
│       └── sample_realtime.html
└── app.py
```

### 推奨依存パッケージ

```toml
[project.dependencies]
streamlit = "^1.36"
requests = "^2.32"
beautifulsoup4 = "^4.12"
pydantic = "^2.7"
geopy = "^2.4"
pandas = "^2.2"
streamlit-local-storage = "^0.0.21"
```

---

## 10. Phase 分割・工数

| Phase | 内容 | 工数見積もり |
|---|---|---|
| 1. 初期化 | pyproject.toml、ディレクトリ構造、`models.py` / `constants.py` の雛形 | 30 分 |
| 2. スクレイパー | `scraper.py` + fixture テスト、TDL URL 設定、キャッシュ | 1 時間 |
| 3. マスタ整備 | `attractions.json`（20-25 件）+ `restaurants.json`（10 件）の座標手測定、`requires_reservation` / `outdoor` フラグ設定 | **3.5-4.5 時間（人力ボトルネック）** |
| 4. 距離・予測 | `distance.py`（パレード横断 + 雨天）、`predictor.py`（雨天対応）、テスト | 1 時間 |
| 5. ルート生成 | `router.py` の TDD 実装、must-visit + DPA + 衝突回避 + 雨天モード | 3.5 時間 |
| 6. UI | `app.py`、各セクション、localStorage、警告表示、雨天トグル | 4 時間 |
| 7. デプロイ | requirements.txt、README、Streamlit Cloud 設定 | 30 分 |
| **合計** | | **約 14 時間** |

バッファ込み **15〜16 時間**。1 日 2 時間ペースで 8 日間。来園日まで 9 日あるので余裕。

### 想定スケジュール

| 日付 | 作業 |
|---|---|
| 5/16 土（今日） | ブレスト → 設計確定 → 実装計画作成 |
| 5/17 日 | Phase 1 + Phase 2 |
| 5/18 月 | Phase 4 |
| 5/19 火 | Phase 3（マスタ整備） |
| 5/20-21 水木 | Phase 5（TDD） |
| 5/22-23 金土 | Phase 6 |
| 5/24 日 | Phase 7 + 統合テスト + 当日リハーサル |
| **5/25 月** | **来園日** 🎢 |

---

## 11. テスト方針

### 11.1 TDD 適用範囲

| モジュール | TDD 適用 | 理由 |
|---|---|---|
| `src/router.py` | ✅ 必須 | ロジック中核。分岐多数 |
| `src/predictor.py` | ✅ 必須 | 数値ロジック、境界条件 |
| `src/distance.py` | ✅ 必須 | パレード補正・雨天補正の境界 |
| `src/scraper.py` | ⚠️ fixture | 実 HTML を保存してテスト |
| `src/models.py` | ⚠️ 最低限 | Pydantic 自身が検証 |
| `app.py` | ❌ 手動 | Streamlit の UI テストは v1 スコープ外 |

### 11.2 主要テストケース

**`tests/test_router.py`**

- 空のスナップショットで例外を投げない
- 全アトラクション運営休止なら空ルート
- priority 5 が priority 3 より先に訪問される
- must-visit が非 must-visit より先に消化される
- must-visit が時間内に収まらない場合 `unvisited_musts` に残る
- DPA ブロックが指定時間に消化される
- DPA 時間窓に間に合わない場合 `dpa_window_missed` 警告
- `requires_reservation=true` は DPA なしでは候補から外れる
- `requires_reservation=true` は DPA 登録時に訪問される
- 固定ブロック衝突時、収まらない候補が弾かれる
- 食事ブロックで current_location が更新される
- 雨天モード時、屋外アトラクションの優先度が下がる

**`tests/test_predictor.py`**

- 30 分以内は現在値を返す
- ピーク時間（11-14）で予測待ち増加
- 夕方以降（19-21）で予測待ち減少
- S tier は C tier より振れ幅大
- 最小待ち時間 5 分でクランプ
- 雨天モード：屋外 -30%、屋内 +20%

**`tests/test_distance.py`**

- 同じエリア内はユークリッド距離ベース
- メインストリート横断 + パレード時間中なら +15 分
- パレード `watch=True` は横断ペナルティ対象外（鑑賞中は移動しない）
- 雨天モード：park_factor が 1.4 → 1.7

**`tests/test_scraper.py`**

- fixture HTML から正しく抽出
- ファジーマッチで `scrape_key` 解決
- `status="closed"` は wait=null
- スクレイピング失敗時、直近スナップショットにフォールバック
- 同セッション5分以内ならキャッシュ

---

## 12. 当日の運用フロー

```
朝 8:00（自宅）
  → URL を開く、localStorage から前日の設定を復元（または初期化）
  → 優先度・must-visit・食事ブロック・パレード時刻を設定

朝 9:00（開園 → 入園）
  → 公式アプリで DPA を購入したらアプリに入力
  → 「更新」→「ルート生成」
  → 推奨ルートに従って最初のアトラクションへ

11:00 ごろ
  → 待ち時間が想定とズレてきたら「更新」→「ルート生成」で再計算
  → 雨が降り始めたら雨天モード ON

昼食後・夕方
  → 同様に再生成

20:00 以降
  → 残り時間でのルート再生成
  → パレード鑑賞 / 夜景アトラクションへ
```

---

## 13. 規約面の注意

- **個人利用に限定**：商用利用・公開禁止
- **GitHub 公開時**：「個人学習目的、商用利用不可」を明示、Disney / OLC 商標は使わない
- **取得頻度**：5 分に 1 回が下限
- **スクレイピング先**：公式サイトのみ（アプリ API 解析は禁止）

---

## 14. v2 以降の将来拡張

1. 当日スナップショットを `data/snapshots/` に永続化（Streamlit Cloud 制約のため外部ストレージ必要）
2. 過去データから時間帯別予測モデル学習
3. DPA 購入候補の最適化（「どれを買うべきか」提案）
4. シー / 複数日対応
5. 動的天気取得（OpenWeatherMap API）
6. PWA 化、オフライン対応

---

## 15. 未決事項（実装時に判断）

実装中・マスタ整備中に確認すべき軽微な論点：

| # | 論点 | 判断タイミング |
|---|---|---|
| 1 | 朝の開園待ち列の扱い（start_time = 9:00 か 9:15 か） | UI で可変にする方向。Phase 6 |
| 2 | スマホ縦画面の操作性（折りたたみアコーディオン） | Phase 6 で実機確認しながら調整 |
| 3 | TIME_FACTOR の TDL 向け調整 | 当日実測してから v2 で調整 |
| 4 | GitHub repo を public / private | Phase 7 で決定（Streamlit Cloud 無料枠は public のみ） |
| 5 | 美女と野獣の `requires_reservation` 値 | Phase 3 マスタ整備時に公式サイトで最終確認 |
| 6 | `MAIN_STREET_BLOCKING_PAIRS` の具体的な組み合わせ | Phase 4 で実地経験 + Google マップで決定 |
| 7 | パレード時刻 | 来園日近くに公式サイトで確定、当日朝に入力 |

---

## 16. 来園日固定情報

| 項目 | 値 |
|---|---|
| 来園日 | **2026-05-25（月曜）** |
| 営業時間 | 9:00-21:00（暫定、5/18 頃に公式で確定） |
| 特別イベント | なし前提 |
| 同行者 | あり想定（閲覧のみ。設定は東郷さんが代表入力） |
| デプロイ先 | Streamlit Community Cloud |

---

## 付録 A：実装前チェックリスト

- [ ] Python 3.11+ がインストール済み
- [ ] uv または poetry が使える
- [ ] Claude Code 環境が動作する
- [ ] Google マップでアトラクション + レストラン座標を取得できる
- [ ] 5/18 頃に来園日（5/25）の営業時間 + パレード時刻を確認する
- [ ] 5/24 までに統合テスト時間を確保する
