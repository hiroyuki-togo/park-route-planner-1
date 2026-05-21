# TDL Route Planner — 進捗ハンドオフ

> 次セッションの Claude Code が状況を即時把握するための引き継ぎファイル。

**最終更新**: 2026-05-21（シミュレーションモード追加後）
**来園日**: 2026-05-25（月）
**残り日数**: 4 日

---

## 1. 現在のステータス

**Phase 1〜6 完了 + 仕様追加（シミュレーションモード）完了**。28 コミット、**テスト 52/52 PASS**、Streamlit 起動確認済み。
プラン §10 想定スケジュールに対して **依然先行**。残るは Phase 7（デプロイ）と、東郷さん側での **シミュレーションモード目視確認**（§3 末尾チェックリスト）。

---

## 2. 完了済みタスク（Task 1〜19）

### Phase 1〜4

| Task | 内容 | コミット |
|---|---|---|
| 1 | プロジェクト scaffold（pyproject.toml、.gitignore、ディレクトリ構造） | `c540d3f` |
| 2 | venv 構築（Python 3.11 を brew で別途インストール）、依存導入 | （commit なし、環境のみ） |
| 3 | `src/constants.py` + 6 テスト | `bb6777b` |
| 4 | `src/models.py`（9 Pydantic モデル）+ 5 テスト | `9446b46` |
| 5 | fixture 保存（HTML + JSON）— ここで重要発見、後述 §5 | `5dd970e` |
| - | 仕様書 §4 と プラン Task 6-8 を JSON API ベースに書き換え | `67cc32c` |
| - | CLAUDE.md / memory.md / archive を初コミット | `dd3cafd` |
| 6 | `src/scraper.py` JSON パース + 4 テスト | `4869122` |
| 7 | ファジーマッチ追加 + 2 テスト | `e09a3bd` |
| 8 | fetch + 5 分キャッシュ + フォールバック + 3 テスト | `7b13478` |
| 9 | `scripts/generate_attractions_template.py` + `data/attractions.json`（21 件、座標 null） | `98dd811` |
| 10 | `scripts/generate_restaurants_template.py` + `data/restaurants.json`（10 件、座標 null） | `06d02f3` |
| 11 | `tests/test_masters.py`（妥当性検証 6 件） | `4bc25ed` |
| 9.5 | xlsx 入力/インポートワークフロー（プラン外、東郷さんの作業効率化） | `7688133` |
| 9.6 | 全 31 件の座標を Excel 経由で取り込み、test_masters.py 全 PASS | `238438a` |
| 12 | `src/distance.py` 距離計算（パーク係数・雨天・パレード横断）4 テスト | `68e6358` |
| 13 | `src/predictor.py` 待ち時間予測（時間帯×人気度、雨天屋外/屋内）7 テスト | `782c7de` |

### Phase 5（ルート生成）— 5/20 完了

| Task | 内容 | コミット |
|---|---|---|
| 14 | `tests/conftest.py` 共通 fixture + `src/router.py` 骨格 + 最小ケース 2 件 | `7b2fc69` |
| 15 | must-visit 優先プール（Task 14 でカバー済、テストのみ追加） | `7cd76a8` |
| 16 | DPA/meal/show/parade 固定ブロック取り込み + `_handle_fixed_block` | `3f09461` |
| 17 | 食事ブロックで current_location 更新（Task 16 でカバー済、テストのみ追加） | `2c5e0fe` |
| 18 | 雨天モード時の屋外優先度ダウン（Task 14 スコア式でカバー済、テスト追加） | `8fffe13` |
| 19 | requires_reservation 未予約 + must の警告（`no_dpa_for_reserved`） | `8fffe13` |

### Phase 6（Streamlit UI）— 5/20 完了

| Task | 内容 | コミット |
|---|---|---|
| 20 | `app.py` 骨組み（cached loaders、session_state init、雨天トグル） | `a1cdd32` |
| 21+22 | アトラクション設定（priority slider + must-visit）+ 食事 / ショー / DPA 入力 | `09a2bfe` |
| 23 | 取得・ルート生成・表示 + ダミー snapshot フォールバック + fetch エラーログ改善 | `c8135e2` |
| — | priority=0 でアトラクションを候補から除外（東郷さん要望） | `5af96ac` |
| 24+25 | localStorage 永続化（日付スコープ）+ CSV 出力 | `ce08b0d` |

### 仕様追加：シミュレーションモード（前日プランニング対応）— 5/21 完了

東郷さん要望「当日にしかプランニングできない／前日に叩き台を作れないか」への回答。
**案 B（履歴データ蓄積）vs 案 A（シミュレーション）** の議論の結果、目的「**心の準備・叩き台**」に合致する案 A を選択。
詳細プランは [/Users/tougouhiroyuki/.claude/plans/vectorized-spinning-boot.md](file:///Users/tougouhiroyuki/.claude/plans/vectorized-spinning-boot.md)。

| Task | 内容 | コミット |
|---|---|---|
| T-S1 | `src/simulator.py` + `tests/test_simulator.py` 単体 5 件（TDD） | `1eef2a1` |
| T-S2 | 統合テスト `test_simulate_then_route` | `33511bb` |
| T-S3 | `app.py` モード切替 radio + 日付選択 + route_date 変数化 + localStorage 分岐 | `7dbe760` |
| T-S4 | テスト 52/52 PASS、Streamlit 起動 HTTP 200 確認、ドキュメント更新 | （本コミット） |

**動作確認の残タスク**（東郷さん側）:

- [ ] `🟢 当日モード`で `must_visits` / 食事 / DPA 設定 → 「🔄 更新」→ 「⚡ ルート生成」が Phase 6 と同じ結果（回帰なし）
- [ ] `🔮 シミュレーションモード`に切替 → 「想定日」が 2026-05-25 で表示
- [ ] シミュモードで「🔮 合成 snapshot 生成」→ 成功メッセージ「合成 snapshot 生成：2026-05-25 9:00 開園想定」
- [ ] そのまま「🔮 シミュレーション」→ 9:00 開始〜終園 21:00 のルートが返る
- [ ] 雨天モード ON で再生成 → 屋外アトラクションの待ち時間が小さく出ること
- [ ] ブラウザ DevTools の Application > LocalStorage で `tdl_settings_{今日}` がシミュ操作中に更新されていないこと
- [ ] 当日モードに戻して既存設定がそのまま残っていること

---

## 3. 次にやること

### 🟢 次回のモード：**Phase 7（デプロイ）** または **残りの仕様見直し論点**

シミュレーションモードが入って、東郷さんの主要要望は満たした。優先順位の候補：

1. **Phase 7 デプロイ**（プラン Task 26-28）— `requirements.txt` 生成、README、GitHub リポジトリ作成、Streamlit Community Cloud デプロイ、統合テスト
2. **PROGRESS.md §3 の仕様見直し論点 A〜D の続き**（A1 スコア式、B1 DPA 警告位置、B5 unvisited_musts の名前表示、等）
3. **シミュレーションモードの目視確認**（上記チェックリスト）→ 不具合があれば優先で修正

### 仕様見直しの候補リスト（次セッションで議論したい論点）

下記は「動かしてみて気になったこと」+ Phase 5/6 で意図的に見送った改善余地。優先度は東郷さんと話し合って決める。

#### A. スコアリング・ロジック関連

- **A1. 「必ず乗る」+ 優先度のスコア式が直感に反する**
  - 現状: `score = priority × EXP_VALUE[人気度] / cost`。priority の差（最大 5 倍）より cost の差（10〜100 倍幅）のほうが効きやすい
  - 検討：必ず乗る同士の順序は cost より priority を強く効かせるべきか、現状維持か
  - 関連ファイル: [src/router.py](src/router.py) `_score()`
- **A2. priority=0 と must-visit の矛盾入力の扱い**
  - 現状: must_visits が pending_must で優先するので priority=0 は無視される（仕様）
  - 検討: UI で警告を出すか、入力時に弾くか、無視のまま放置か

#### B. UI / UX 関連

- **B1. DPA 未登録警告の表示位置**
  - 現状: 該当アトラクション行の直下に出るので長い一覧で見落としやすい
  - 検討: アトラクション設定セクション上部にサマリ表示（[Phase 6 動作確認時に (c) 不要 判断で見送り]）
- **B2. アトラクション設定の並び順**
  - 現状: `(area, name)` でソート
  - 検討: 人気度順 or popular-tier S 群を上にまとめる、エリア見出しを入れるなど
- **B3. ルート結果の表示**
  - 現状: テキスト 1 行 / step
  - 検討: 累計時間・残り時間の表示、エリア移動の視覚化、地図プレビュー（v2 候補）
- **B4. 食事ブロックの初期値**
  - 現状: 1 件目 12:00-13:30、2 件目 19:00 開始（プラン規定）
  - 検討: TDL 営業時間（5/25 確定）に応じて変える、来園日固有の初期値にするなど
- **B5. unvisited_musts の表示が ID のまま**
  - 現状: `- pooh` のように ID 表記
  - 検討: 名前表記に変える（attractions_by_id ルックアップ）

#### C. 待ち時間予測ロジック

- **C1. 予測精度の限界（仕様）**
  - 既知制約: 朝20分→昼60分の外れは仕様（CLAUDE.md §4 で明示済）
  - 来園当日は 2-3 回再生成する運用前提。**過剰実装はしない**
- **C2. `get_time_factor(21)` のフォールスルー**
  - 現状: 閉園時刻ガードはルーター側で担保（`current_time < close_time`）
  - 検討: predictor 側でも明示ガードを入れるか、現状維持か

#### D. データ・運用関連

- **D1. ダミー snapshot の扱い**
  - 現状: `scripts/generate_dummy_snapshot.py` で随時生成、`data/snapshots/` は gitignore
  - 検討: 来園日リハーサル用に複数パターン（朝・昼・夜）の固定 dummy を別ディレクトリに置くか
- **D2. `requires_reservation` 対象が 1 件だけ**
  - 現状: 「美女と野獣"魔法のものがたり"」のみ
  - 確認: 来園日時点で他に予約必須化されるアトラクションがないか、5/24 リハーサル時に再確認

### Phase 7（デプロイ）— 仕様見直し後に着手

[実装計画 Task 26](docs/superpowers/plans/2026-05-16-tdl-route-planner.md) — 2620 行〜。

- Task 26: `requirements.txt` 生成 + `README.md`（個人学習目的・商用不可を明示）
- Task 27: GitHub リポジトリ作成 + Streamlit Community Cloud デプロイ
- Task 28: 統合テスト（実 API + UI 通しでの動作確認）

### Phase 6 で逸脱したプラン記述（次セッションが混乱しないよう明記）

1. **fetch 失敗時の挙動を強化**: プラン未記載、`src/scraper.py` で例外を logger.warning で出すように改善（silent swallow を回避）
2. **ダミー snapshot 生成スクリプト追加**: プラン未記載、ライブ API レート制限時のフォールバック素材として `scripts/generate_dummy_snapshot.py` を追加
3. **priority=0 でアトラクション除外**: プラン未記載、東郷さん要望で実装。`Attraction.default_priority` の lower bound を 1→0 に緩和、`_candidate_pool` で除外
4. **import 配置**: プランは関数内 import を多用、実装では PEP 8 に沿って冒頭に集約

### Phase 6 動作確認時の発見

- **ライブ API レート制限の再発**: curl で 30 秒タイムアウト確認。ダミー snapshot でフォールバック動作の確認は完了。来園日前（5/23-24）に実 API テストを再度実施する想定
- **`requires_reservation=True` のアトラクションは「美女と野獣"魔法のものがたり"」1 件のみ**（マスタ確認結果）

### lessons.md に追記した学び

- **#12 候補枯渇 vs idle until next event**（Task 16）
- **#13 プランの設計判断は実装前に必ず東郷さんに確認**（Task 16）
- **#14 UI 失敗パスから先に試す + silent except は UX デバッグの敵**（Phase 6 動作確認）
- **#15 個人ツールには「決定的な fixture 生成スクリプト」をペアで作る**（ダミー snapshot）
- **#16 仕様質問には「結論先・式は補足」**（スコア式の説明の反省）
- **#17 「データ蓄積 vs 合成シミュレーション」の ROI 判断**（5/21 シミュレーションモード追加時）

### 残り Phase スケジュール

- 5/20 水 → **Phase 5 + 6 完了**
- 5/21 木 → **シミュレーションモード追加完了**（前日プランニング対応、4h で実装）
- 5/22 金 → 予備日 or Phase 7 着手
- 5/23 土 → Phase 7（デプロイ）+ リハーサル
- 5/24 日 → 予備日（不具合対応・微調整）
- 5/25 月 → 来園日

---

## 4. 重要な設計変更（プラン外）

### スクレイパーを HTML → JSON API に切替

**原因**：TDL 公式サイトはクライアントサイドレンダリング（CSR）。`curl` で取得した HTML には待ち時間データが含まれず、JavaScript が `/_/realtime/tdl_attraction.json` から取得して描画する構造。

**対応**：仕様書 §4 と プラン Task 6-8 を JSON API ベースに書き直し済み（コミット `67cc32c`）。
JSON エンドポイント：`https://www.tokyodisneyresort.jp/_/realtime/tdl_attraction.json`

**副次効果**：
- BeautifulSoup の必要性が低下（pyproject.toml には残しているが scraper では import 不要）
- DPA 状況・スタンバイパス状況が `DPAStatusCD` / `FsStatusCD` で取れる → v2 で活用余地
- 名前は正式名で揺れ少、ファジーマッチは保険として残す

---

## 5. 引き継ぎ事項（コードから読み取れない判断・状況）

### 既知の課題

| 項目 | 対処タイミング |
|---|---|
| `get_time_factor(21)` がフォールスルーで `1.0` を返す。閉園時刻のガード未実装 | Task 13 では呼び出し側保証を選択（未実装）。Phase 5 ルーター実装時に target_time が CLOSE_TIME を超えないことをルーター側で担保すれば実害なし |
| `pyproject.toml` に `beautifulsoup4` が残っているが scraper では未使用 | Phase 7 で `requirements.txt` 生成時に判断（残してもサイズ影響軽微） |
| `.claude/` ディレクトリが untracked のまま | 必要なら `.gitignore` に追記。今は無害 |
| omnibus の初期入力座標が TDL 範囲外（駐車場付近）→ 東郷さんと相談しワールドバザール内に修正済 | 解決済（`238438a`）。同種のミス防止のため lessons.md #11 に分布ベース sanity check を記録 |

### ライブ API のレート制限

過去セッションで `fetch_realtime_wait_times()` の実 API 呼び出しが **タイムアウト** したことあり。原因の可能性：

- Task 5 で 1.8MB HTML をダウンロードした直後の連続アクセス → IP ベースのレート制限
- アプリ側のキャッシュ（5 分 TTL）と無関係に、外側のネットワーク層で抑制された

**対処**：時間を置けば回復するはず。コードロジック上の問題ではない（オフラインテスト 37/37 PASS）。Phase 5 はルーター実装で実 API を叩く必要なし。Phase 6（Streamlit UI）の動作確認時に再確認。

### 確定した設計判断

- DPA 使用前提（コアアトラクションは DPA で乗る）
- 同行者は URL 共有による閲覧のみ（協調編集機能は v1 不実装）
- パレード：fixed_block 化、`watch=True` なら鑑賞・`False` ならメインストリート横断 +15 分ペナルティ
- 雨天モード：UI トグル、屋外 -30% 待ち時間 / 屋内 +20% / 移動係数 1.4→1.7 / 屋外 experience_value 0.7 倍
- 設定永続化：localStorage、日付スコープ（`tdl_settings_{YYYY-MM-DD}`）

---

## 6. 環境メモ

- 作業ディレクトリ：`/Users/tougouhiroyuki/Projects/disney/`
- venv：`.venv/`（Python 3.11.15）
- pytest 実行：`.venv/bin/pytest -v`
- システム Python は 3.9.6（pyproject の `>=3.11` を満たさず、brew で 3.11 を別途インストール済み）
- GitHub アカウント：07jdp353@gmail.com（git config 設定済み、別プロジェクト [人事評価制度] と共存）
- GitHub プッシュは Phase 7（5/24）で実施予定。今はローカル止まり

---

## 7. 関連ファイル

- [仕様書（正本）](docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md)
- [実装計画](docs/superpowers/plans/2026-05-16-tdl-route-planner.md)
- [プロジェクト指示](CLAUDE.md)
- [意思決定経緯](memory.md)
- [教訓](lessons.md)
- [TDS 向け旧仕様（参考）](archive/ディズニープラン-TDS.md)

---

## 8. 次セッション開始時のおすすめプロンプト

```
ディズニーランドのルート生成ツール、Phase 1〜6 まで完了済みです。
今日は細かい仕様の見直しをしたいので、PROGRESS.md §3 の「仕様見直しの候補リスト（A〜D）」を読んで、それぞれの論点を整理して提示してください。私が優先順位を決めるので、まずは候補一覧と各論点の現状＋検討すべき軸を一覧化するところから。

事前に `.venv/bin/pytest -q` で 46/46 PASS を確認し、`.venv/bin/streamlit run app.py` で UI が起動することも見ておいてください。
```

### 引き継ぎチェックリスト（次セッション冒頭で確認すること）

- [ ] `git log --oneline -10` で Phase 6 関連 5 コミット（`a1cdd32 / 09a2bfe / c8135e2 / 5af96ac / ce08b0d`）+ PROGRESS 更新が見えること
- [ ] `git status` でクリーン
- [ ] `.venv/bin/pytest -q` で **46 passed**
- [ ] `.venv/bin/streamlit run app.py` で UI が起動しブラウザで表示されること（目視）
- [ ] CLAUDE.md / lessons.md / PROGRESS.md §3 を読んで仕様見直しの論点を把握
- [ ] **コードに手を入れる前に「論点一覧 → 東郷さんの優先順位 → 個別議論」の順を厳守**（いきなり改修に走らない）

### 仕様見直しを進めるときの注意

1. **A〜D の論点は独立**: 1 つずつ「ブレインストーミング → 合意 → 実装 → 確認」のサイクルで進める。複数同時改修は避ける（lessons.md #13 の教訓）
2. **見直し中にプラン外の改修が増える**: コミット粒度を細かく保つ。1 論点 1 コミットを基本に
3. **UI 改修は streamlit リロードで都度確認**: 単独テストではカバーしきれない見た目の確認が必要
4. **「来園日に実用できるか」が最終判定基準**: 過剰実装は捨てる。CLAUDE.md §4「精度向上のための過剰実装は入れない」を守る
