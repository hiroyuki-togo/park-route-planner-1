# TDS Route Planner 設計仕様書

> 東京ディズニーシー（TDS）来園日に使う、個人ツールとしての終日ルート自動生成アプリ。
> 想定実装環境：Python 3.11+ / Streamlit / Claude Code併用。
> 想定来園条件：**特別イベントなしの平日**。

---

## 0. 全体像

```
┌─────────────────────────────────────────────────┐
│  Streamlit App (app.py)                         │
│   ├─ 優先度・食事・ショー時間の手動入力        │
│   └─ 推奨ルート表示                             │
│                                                 │
│  Core Modules (src/)                            │
│   ├─ scraper.py     → 公式サイトから待ち時間   │
│   ├─ predictor.py   → 時間帯による待ち時間補正 │
│   ├─ distance.py    → 移動時間計算             │
│   └─ router.py      → 貪欲法でルート生成       │
│                                                 │
│  Data (data/)                                   │
│   ├─ attractions.json  : 座標・所要時間マスタ  │
│   └─ snapshots/        : 取得履歴              │
└─────────────────────────────────────────────────┘
```

---

## 1. データモデル

### 1.1 `data/attractions.json`（マスタデータ）

```json
{
  "park": "TDS",
  "open_time": "09:00",
  "close_time": "21:00",
  "entrance": { "lat": 35.6262, "lng": 139.8830 },
  "attractions": [
    {
      "id": "soaring",
      "name": "ソアリン:ファンタスティック・フライト",
      "scrape_key": "ソアリン",
      "area": "メディテレーニアンハーバー",
      "lat": 35.6275,
      "lng": 139.8845,
      "experience_time_min": 5,
      "queue_walk_min": 5,
      "default_priority": 5,
      "dpa_eligible": true,
      "popularity_tier": "S"
    }
  ]
}
```

**フィールド定義**

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string | 内部識別子。snake_case |
| `scrape_key` | string | 公式サイト表記と照合するためのキー。揺れに注意 |
| `lat`, `lng` | float | 待機列入口の緯度経度（Googleマップで手動測定） |
| `experience_time_min` | int | 乗車・体験時間（待機列移動も含む） |
| `default_priority` | int (1-5) | UI初期値。1=任意、5=必須 |
| `dpa_eligible` | bool | プレミアアクセス対象か |
| `popularity_tier` | enum | S/A/B/C。待ち時間予測の係数に使用 |

### 1.2 待ち時間スナップショット

```json
{
  "timestamp": "2026-05-XX 09:15:00",
  "park": "TDS",
  "data": [
    { "name": "ソアリン", "wait_min": 90, "status": "operating" },
    { "name": "タワー・オブ・テラー", "wait_min": null, "status": "closed" }
  ]
}
```

`status`: `operating` / `closed` / `unknown` の3値。

---

## 2. スクレイピング仕様（`src/scraper.py`）

### 2.1 対象URL

`https://www.tokyodisneyresort.jp/tds/realtime/attraction/`

### 2.2 抽出ルール

| 要素 | CSS Selector | 加工 |
|---|---|---|
| アトラクション名 | `.realtime-attr-name` | `.strip()` で前後空白除去、`u3000`（全角スペース）→半角に正規化 |
| 待ち時間 | `.attr_wait` | `"分"`で分割、`.isdecimal()`で数値判定、それ以外は`null` |
| 運営状況 | `.attr_wait`内テキスト | 「案内終了」「運営状況確認中」→`closed`/`unknown` |

### 2.3 設計要件

- **アクセス頻度**：5〜10分に1回まで（規約面と先方サーバー負荷の両面から）
- **User-Agent**：実在のブラウザ文字列を指定
- **タイムアウト**：30秒
- **リトライ**：3回（指数バックオフ）
- **失敗時**：直近のスナップショット（`data/snapshots/`）にフォールバック
- **出力**：`data/snapshots/{YYYY-MM-DD}_{HHMM}.json`

### 2.4 エッジケース

- DOM変更で抽出失敗 → ログ＋直近スナップショット使用
- 全アトラクション運営休止（早朝・天候不順）→ そのまま記録、ルート生成側で扱う
- アトラクション名の表記揺れ → `attractions.json` の `scrape_key` でファジーマッチ（`difflib.get_close_matches`、閾値0.85）

---

## 3. 待ち時間予測（`src/predictor.py`）

過去データなしで平日・イベントなしを前提にした単純モデル。

### 3.1 時間帯補正係数

```python
TIME_FACTOR = {
    (9, 10):  0.7,   # 開園直後は短い
    (10, 11): 0.9,
    (11, 14): 1.3,   # ピーク
    (14, 17): 1.2,
    (17, 19): 1.0,
    (19, 21): 0.7,   # 夕方以降は減る
}
```

### 3.2 人気度係数

```python
POPULARITY_FACTOR = { "S": 1.0, "A": 0.9, "B": 0.8, "C": 0.7 }
```

人気アトラクションほど時間帯による振れ幅が大きい、という仮説。

### 3.3 予測式

```python
def predict_wait(attraction, current_wait, current_time, target_time):
    """
    現在の待ち時間から、target_time時点の待ち時間を予測
    """
    if target_time - current_time < timedelta(minutes=30):
        return current_wait  # 30分以内は現在値をそのまま使う

    factor_now = get_time_factor(current_time.hour)
    factor_then = get_time_factor(target_time.hour)
    pop_factor = POPULARITY_FACTOR[attraction.popularity_tier]

    # 時間帯間の変化率に人気度補正をかける
    delta = (factor_then - factor_now) * pop_factor
    return max(5, current_wait * (1 + delta))
```

**精度の限界**：過去履歴がないため、外す可能性は高い。実用上は「朝のスナップショット時点の待ち時間」を起点に、ピーク時間帯は1.3倍、夜は0.7倍程度に補正する目安として使う。

---

## 4. 距離・移動時間（`src/distance.py`）

### 4.1 計算式

```python
from geopy.distance import geodesic

def travel_time_min(loc_a, loc_b):
    distance_m = geodesic(loc_a, loc_b).meters
    walking_speed_m_per_min = 67  # 4km/h ≒ 67m/min
    park_factor = 1.4              # 通路の曲がりを考慮した係数
    return distance_m / walking_speed_m_per_min * park_factor
```

### 4.2 設計上の注意

- ディズニーシーは**水路で分断**されているため、ユークリッド距離が実移動時間を大きく下回るケースがある（例：ロストリバーデルタ ↔ メディテレーニアンハーバー）
- 対策：エリア間の移動に「最小コスト」を別途定義してオーバーライド

```python
AREA_MIN_TIME = {
    ("メディテレーニアンハーバー", "アメリカンウォーターフロント"): 8,
    ("メディテレーニアンハーバー", "ロストリバーデルタ"): 12,
    # ...
}
```

---

## 5. ルート生成アルゴリズム（`src/router.py`）

### 5.1 スコアリング関数

```
Score(候補 i, 現在時刻 t, 現在地 loc) = 
    (priority[i] × experience_value[i]) 
    ÷ (travel_time(loc, location[i]) + predicted_wait[i, t] + experience_time[i])
```

- `experience_value[i]`：人気度tier S=10, A=7, B=5, C=3
- `priority[i]`：UI入力1-5
- 分母の単位：分

### 5.2 制約

| 制約 | 扱い |
|---|---|
| 開園・閉園時間 | 9:00〜21:00を上下限 |
| 既訪問 | 候補から除外（リピート可フラグは将来対応） |
| 食事時間 | UI指定の時間ブロックを予約席として確保 |
| パレード/ショー | UI指定の鑑賞時間ブロックを確保 |
| 運営休止 | `status != "operating"` の場合は候補から除外 |

### 5.3 擬似コード

```python
def generate_route(snapshot, attractions, constraints, priorities):
    current_time = constraints.start_time  # 9:00
    current_location = constraints.entrance
    blocks = sorted(constraints.fixed_blocks)  # 食事・ショー
    route = []
    visited = set()

    while current_time < constraints.close_time:
        # 固定ブロック処理
        if blocks and blocks[0].start <= current_time:
            block = blocks.pop(0)
            route.append({"type": block.type, "start": block.start, "end": block.end})
            current_time = block.end
            current_location = block.location or current_location
            continue

        # 候補評価
        candidates = [a for a in attractions if a.id not in visited
                      and is_operating(a, snapshot)]
        if not candidates:
            break

        scored = []
        for c in candidates:
            travel = travel_time_min(current_location, (c.lat, c.lng))
            arrive_time = current_time + timedelta(minutes=travel)
            wait = predict_wait(c, get_current_wait(c, snapshot), 
                                snapshot.timestamp, arrive_time)
            cost = travel + wait + c.experience_time_min
            value = priorities[c.id] * EXP_VALUE[c.popularity_tier]
            scored.append((value / cost, c, travel, wait))

        best_score, best, travel, wait = max(scored, key=lambda x: x[0])
        
        route.append({
            "type": "attraction",
            "id": best.id,
            "arrive": current_time + timedelta(minutes=travel),
            "ride_start": current_time + timedelta(minutes=travel + wait),
            "ride_end": current_time + timedelta(minutes=travel + wait + best.experience_time_min),
            "travel_min": travel,
            "wait_min": wait,
        })
        current_time += timedelta(minutes=travel + wait + best.experience_time_min)
        current_location = (best.lat, best.lng)
        visited.add(best.id)

    return route
```

### 5.4 計算量

- アトラクション数 ≒ 25
- ステップ数 ≒ 15-20（1日で回れる現実的な数）
- 1ステップあたり25個の候補評価
- 全体：O(N²) ≒ 500回程度の評価。瞬時に完了

---

## 6. UI仕様（`app.py`、Streamlit）

### 6.1 画面構成

```
┌─────────────────────────────────────┐
│ 🎢 TDS Route Planner                │
│ 最終取得: 09:15 [🔄 更新]            │
├─────────────────────────────────────┤
│ ▼ 優先度設定 (★1-5)                  │
│ ソアリン         [★★★★★]          │
│ センター・オブ・[★★★★★]          │
│ タワー・オブ・  [★★★★☆]          │
│ ...                                  │
├─────────────────────────────────────┤
│ ▼ 食事・ショー時間                  │
│ 昼食 [12:00] - [12:45]               │
│ 夕食 [18:00] - [19:00]               │
│ ☑ ハーバーグリーティング 11:00      │
│ ☑ ビリーヴ! 20:00                    │
├─────────────────────────────────────┤
│ [⚡ ルート生成]                      │
├─────────────────────────────────────┤
│ ▼ 推奨ルート (生成時刻: 09:16)      │
│ 09:00 ソアリン      待20分 ⭐⭐⭐⭐⭐│
│ 09:50 トイマニ       待35分 ⭐⭐⭐⭐│
│ 10:55 タワー         待40分 ⭐⭐⭐⭐│
│ 12:00 🍴 昼食                        │
│ ...                                  │
│ [📥 CSV出力] [📋 コピー]            │
└─────────────────────────────────────┘
```

### 6.2 状態管理

`st.session_state` に以下を保持：
- `priorities: dict[str, int]`
- `meal_blocks: list[Block]`
- `show_blocks: list[Block]`
- `last_snapshot: dict`
- `current_route: list`

---

## 7. ディレクトリ構造

```
tds-route-planner/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── data/
│   ├── attractions.json        # マスタ（手動整備）
│   └── snapshots/              # 自動生成
├── src/
│   ├── __init__.py
│   ├── scraper.py
│   ├── models.py               # Pydantic models
│   ├── predictor.py
│   ├── distance.py
│   ├── router.py
│   └── constants.py
├── tests/
│   ├── test_scraper.py
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
```

---

## 8. 実装フェーズ分割（Claude Code指示用）

各フェーズの末尾に **Claude Code に投げる指示テンプレート**を付けています。コピペで使えます。

### Phase 1：プロジェクト初期化（30分）

```
TDS Route Plannerプロジェクトを初期化してください。
- pyproject.toml でPython 3.11プロジェクトをセットアップ
- 依存: streamlit, requests, beautifulsoup4, pydantic, geopy, pandas, pytest
- 設計仕様書のディレクトリ構造を作成
- .gitignore (Python標準 + data/snapshots/)
- src/constants.py に開園・閉園時間、TIME_FACTOR等を定義
- src/models.py にPydanticで Attraction, WaitTimeSnapshot, RouteStep を定義
```

### Phase 2：スクレイパー実装（1時間）

```
src/scraper.py を実装してください。
- 仕様書 §2 に準拠
- 関数 fetch_realtime_wait_times() -> WaitTimeSnapshot
- BeautifulSoupで .realtime-attr-name と .attr_wait を抽出
- 失敗時は data/snapshots/ の直近ファイルにフォールバック
- 取得結果を data/snapshots/{YYYY-MM-DD}_{HHMM}.json に保存
- tests/test_scraper.py で fixtures/sample_realtime.html を使ったテスト
  (実際のHTMLを保存しておく)
- アクセス頻度制限: 同日内で前回取得から5分以内ならキャッシュを返す
```

### Phase 3：マスタデータ整備（2-3時間、半手動）

```
data/attractions.json を作成します。
ディズニーシーの全アトラクション約25件について以下を埋めてください。
- まず雛形JSONを生成（id, name, area, experience_time_min, popularity_tier）
  - エリア: メディテレーニアンハーバー、アメリカンウォーターフロント、
            ポートディスカバリー、ロストリバーデルタ、アラビアンコースト、
            マーメイドラグーン、ミステリアスアイランド、ファンタジースプリングス
  - popularity_tier: S=ソアリン/トイマニ/タワー/センター/アナ雪/ピーターパン/ラプンツェル
                     A=インディ/レイジングスピリッツ/タートルトーク
                     B/C=その他
- lat/lng は私が手動で埋めるので、null で出力
- scrape_key は公式サイトの表記を確認しながら埋める
```

座標は Google マップで「ソアリン入口」等を右クリック→座標コピーで取得。25件で30〜40分。

### Phase 4：距離・予測モジュール（30分）

```
src/distance.py と src/predictor.py を実装してください。
- 仕様書 §3 と §4 に準拠
- src/constants.py の AREA_MIN_TIME も定義
- pytest で確認: 
  - 既知の2点間（ソアリン→センター）の移動時間が想定範囲内
  - 朝9時と昼13時で predict_wait の結果が異なる
```

### Phase 5：ルート生成（1.5時間）

```
src/router.py を実装してください。
- 仕様書 §5 の擬似コードに準拠
- 関数 generate_route(snapshot, attractions, constraints, priorities) -> list[RouteStep]
- constraints は Pydantic model (start_time, close_time, entrance, fixed_blocks)
- priorities は dict[attraction_id, int]
- tests/test_router.py:
  - 空のスナップショットでも例外を投げない
  - 全アトラクション運営休止なら空のルートを返す
  - 優先度5を最優先で訪問する
```

### Phase 6：Streamlit UI（2時間）

```
app.py を実装してください。
- 仕様書 §6 のレイアウト
- セクション:
  1. ヘッダー: 最終取得時刻 + 更新ボタン
  2. 優先度設定: st.slider で各アトラクション1-5
  3. 食事ブロック: st.time_input × 2
  4. ショー鑑賞: st.checkbox + st.time_input
  5. 生成ボタン
  6. ルート表示: st.dataframe + 各行のスタイリング
- st.session_state で状態管理
- 生成結果のCSV出力ボタン
- ローカル起動: streamlit run app.py
```

### Phase 7：デプロイ（30分）

```
Streamlit Community Cloud にデプロイする手順を整えてください。
- requirements.txt (pyproject.tomlから生成)
- README.md にデプロイ手順
- secrets管理が必要なものはないので、GitHubのpublic repoでOK
```

---

## 9. 当日の運用フロー

```
朝8:00（自宅）
  → アプリ起動、優先度・食事時間を設定

朝9:00（開園）
  → 「更新」→「ルート生成」
  → 推奨ルートを確認、最初のアトラクションへ

11:00 ごろ
  → 待ち時間が想定とズレてきたら「更新」→「ルート生成」で再計算

昼食後・夕方
  → 同様に再生成
```

リアルタイム動的最適化ではなく、**「気になったら再生成」運用**で十分。

---

## 10. 将来拡張（v2以降）

1. **待ち時間履歴の蓄積**：来園日に取得したデータをCSVで残し、次回以降の予測精度向上に使う
2. **DPA統合**：取得したDPAの時間をfixed_blockとして自動投入
3. **過去データ学習**：複数来園分のデータが溜まったら時間帯別予測モデルを学習
4. **複数日対応**：ランド・シー両対応、滞在中の最適化
5. **PWA化**：スマホホーム画面に追加、オフライン対応

---

## 11. 規約面の注意（再掲）

- ⚠️ **個人利用に限定**：商用利用・公開は規約違反リスクが高い
- ⚠️ **GitHub公開する場合**：「個人学習目的、商用利用不可」を明示、Disney/OLC商標は使わない
- ⚠️ **取得頻度**：5分に1回を下限。連続アクセスはサーバー負荷増になる

---

## 付録A：チェックリスト

実装開始前に確認：

- [ ] Python 3.11+ がインストールされている
- [ ] uv または poetry が使える
- [ ] Claude Code が動いている
- [ ] Google マップでアトラクション座標を取得できる
- [ ] 来園日が確定している（営業時間を確認）

来園日前日に確認：

- [ ] スクレイパーが正常動作する
- [ ] ローカルでアプリが起動する
- [ ] Streamlit Cloud にデプロイ済み（モバイルから開ける）
- [ ] 優先度設定がスマホで操作しやすい
- [ ] 当日の営業時間に合わせて `attractions.json` を調整