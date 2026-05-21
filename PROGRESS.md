# TDL Route Planner — 進捗ハンドオフ

> 次セッションの Claude Code が状況を即時把握するための引き継ぎファイル。

**最終更新**: 2026-05-21（デザイン適用 + UX 微改善 完了後 / 同日夜）
**来園日**: 2026-05-25（月）
**残り日数**: 4 日

---

## 1. 現在のステータス

**Phase 1〜6 完了 + シミュレーション + 当日モード実運用 + デザイン適用 + UX 微改善 完了**。
37 コミット、**テスト 59/59 PASS**、Streamlit 起動確認済 + 東郷さん目視確認済。
今日（5/21）のセッションで **Theme Park Warm UI**（theme.py / .streamlit/config.toml）と
論点 14 件の整理が完了し、推奨実装枠 5 件（A2 / B5 / C2 / E3 / F1）も全て適用。
残るは **Phase 7（デプロイ、5/22-23 目標）** と、**5/18 営業時間確定後・5/24 リハ時の追従**。

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
| T-S4 | テスト 52/52 PASS、Streamlit 起動 HTTP 200 確認、ドキュメント更新 | `3646ecf` |
| T-R1 | リセットボタン 2 種（🧹 セッション / 🗑 完全）を「更新」「ルート生成」行に追加、2 段階確認、widget key 削除、`storage.deleteItem(today_key)` | `432c4ba` |
| T-R2 | 「DPA だけ消えて他は戻らない」問題への根本対応。widget key に `_{reset_token}` suffix を付与し、Streamlit の widget 内部 state を確実に破棄させる | `25f7f23` |

### 仕様追加：当日モードの実運用対応（現在時刻 / 現在位置 / 乗った除外）— 5/21 完了

シミュレーションができたことで、当日モードを「**現在時刻から / 現在位置から / 乗ったやつは除外**」してリアルタイム再生成する用途に振り直した。シミュ＝事前叩き台、当日＝インクリメンタル再生成 という役割分担になった。
詳細プランは [/Users/tougouhiroyuki/.claude/plans/vectorized-spinning-boot.md](file:///Users/tougouhiroyuki/.claude/plans/vectorized-spinning-boot.md)。

| Task | 内容 | コミット |
|---|---|---|
| T-D1 | `src/router.py` の `generate_route()` に `visited` パラメータ追加（後方互換）、`must_visits -= visited` ガード、test_router.py に 3 件追加 | `46c6b8b` |
| T-D2〜T-D4 | session_state に `visited_attractions`、当日モードのみ「現在時刻」「現在位置」「乗った」を UI 追加、constraints の start_time / entrance / visited 構築変更、localStorage 復元・保存対象 | `2874f71` |
| T-D5 | 動作確認 + ドキュメント更新 | `183061c` |
| T-D6 | 過去の固定ブロックを冒頭で除外、進行中ブロックは `arrive=max(block.start, current_time)` に丸める。「現在時刻より前の時間がルートに出る」バグ修正、テスト 2 件追加 | `6c49c5a` |

**動作確認結果**：すべて東郷さん側 OK（5/21 セッション内で確認済）。

**動作確認の残タスク**（東郷さん側）:

- [x] シミュレーションモードの基本動作（5/21 東郷さん確認済「いいと思う」）
- [ ] `🧹 セッション`リセット押下 → 2 段階確認 → 設定が初期化される、リロード後に localStorage から復元される
- [ ] `🗑 完全`リセット押下 → 2 段階確認 → 設定が初期化され、リロード後も空のまま
- [ ] リセット後、weather toggle・優先度 slider・must-visit チェック・食事/ショー/DPA expander 内も全部リセットされていること（widget key 削除の効き目）

### デザイン適用 + UX 微改善（Theme Park Warm v2 / v2.1 + 推奨 5 件） — 5/21 完了

東郷さん事前準備の `theme.py` v2（CSS インジェクション + ルートカードレンダラ）と `.streamlit/config.toml` を取り込み、Streamlit デフォルト UI を「**Theme Park Warm**」（アイボリー背景 + 暖色オレンジ）へ全面移行。同セッション内で論点 14 件を整理し、推奨実装枠 5 件を全て適用。

| コミット | 内容 |
|---|---|
| `3f6efb8` | **theme infra + F1**：theme.py（505 行、CSS + `render_route_step()`）/ `.streamlit/config.toml` / app.py に `inject_theme()` 統合 + 4 ボタンに `key=`（`btn_fetch` / `btn_gen` / `btn_reset_sess` / `btn_reset_full`）+ ルート表示を `render_route_step()` 置換。確認ダイアログの「はい、リセット」を `type="primary"`（オレンジ）から danger 系（赤塗）に変更（`btn_confirm_reset` key 経由） |
| `bc42e73` | **C2 defensive guard**：`get_time_factor(hour)` が 9-21 外で 1.0 フォールスルーする問題に明示ガード（< 9 / >= 21 で 0.7）+ 境界値テスト 2 件追加。テスト 57 → 59 PASS |
| `ea41e0b` | **UX 微改善 3 件**：A2 = 「必ず乗る」+ 優先度 0 の矛盾警告 / B5 = 未消化 must を ID ではなく名前表示 / E3 = 「⟳ いま」ボタン（現在時刻フィールドを `datetime.now()` に戻す、`now_token` suffix で widget 再描画） |

#### 同セッションで判断した「据置」枠（7 件）

「過剰実装は入れない」（CLAUDE.md §4）原則と整合する形で、以下は **触らない** と判断:

- **A1**（スコア式）— cost が支配する現状の挙動は実走前に変えない
- **B2**（並び順）— 21 件なら `(area, name)` で十分
- **B3**（ルート表示の累計時間 / 残り時間 / 地図）— カード化済で v1 は満足ライン。地図プレビューは v2
- **C1**（予測精度）— 仕様。当日 2-3 回再生成でカバー
- **E1**（カードに「✓ 消化済み」）— アトラクション設定の「乗った」と機能重複
- **E2**（乗った一括クリア）— 既存リセットでカバー
- **E4**（途中入園シナリオを sim に追加）— sim は心の準備用、当日モードがリアル運用（lessons #18 と整合）

#### 補足：CSS で 1 件解決できなかった案件（**深追いせず据置**）

`st.time_input` / `st.selectbox` のドロップダウン右側に細い縦線が残る件。Chrome MCP 経由で実 DOM をインスペクションした結果、対象 input の `getComputedStyle().caretColor` は実際に `rgba(0,0,0,0)` で **CSS は意図通り効いていた**ことが判明（= キャレットではなく別の baseweb 内部要素が描画している可能性大）。優先度低と判断して 12 セレクタの defensive な caret-color ルール（theme.py）はそのまま残置（無害、将来 baseweb 更新で効く可能性もある）。学びは lessons #20 に記録。

**動作確認の残タスク**（東郷さん側、ブラウザを Cmd+Shift+R 後）:

- [ ] **F1**：リセット確認ダイアログの「はい、リセット」が**赤塗りつぶし**（オレンジでない）
- [ ] **A2**：アトラクション設定で「必ず乗る」と優先度 0 を同時に設定すると、該当行の下にオレンジ警告が出る
- [ ] **B5**：must を満たせない条件でルート生成 → 警告に **ID ではなく名前**（例「美女と野獣"魔法のものがたり"」）で表示
- [ ] **E3**：当日モードで「現在時刻」フィールド下の「⟳ いま」ボタンを押すと現在時刻に戻る

---

## 3. 次にやること

### 🟢 次回のモード：**Phase 7（デプロイ）+ 情報待ち追従**

5/21 セッションで CSS / UX 微改善まで完了。仕様面はほぼ凍結。
次回（5/22 以降）は **Phase 7（デプロイ）** が主題。並行で 5/18 以降に公式から営業時間が出ていれば B1/B4 を追従、5/23-24 で D1/D2（リハ準備）。

#### A. Phase 7（デプロイ）— 主題、推奨実施日 5/22-23

プラン Task 26-28：

- **Task 26**：`requirements.txt` 生成（`pyproject.toml` の `[project] dependencies` から書き出し）+ `README.md` 作成（個人学習目的・商用不可を明示）
- **Task 27**：GitHub リポジトリ作成（東郷さんは GitHub 不慣れなので PR / branch / remote 等の用語は省略しない＝lessons #4）+ Streamlit Community Cloud デプロイ
- **Task 28**：統合テスト（デプロイ環境で当日モード + シミュモード両方を回す。**theme.py の CSS / `.streamlit/config.toml` の `primaryColor` が Cloud 側で確実に反映されるか**が地味な確認ポイント）

工数：半日〜1 日想定。

#### B. 情報待ち枠（5/18-24 に着手）

| 項目 | 内容 | トリガ |
|---|---|---|
| B1 | DPA 未登録警告のサマリ位置（`requires_reservation` が増えたら冒頭サマリ追加） | 5/18 公式営業時間発表 |
| B4 | 食事ブロック初期値を 5/25 営業時間にハードコード | 5/18 公式営業時間発表 |
| D2 | `requires_reservation` 対象アトラクション再確認（現状は美女と野獣 1 件のみ） | 5/24 リハ時 |
| D1 | 朝・昼・夜の固定 dummy snapshot 3 パターンを `data/snapshots/` 外の別ディレクトリに生成 | 5/23-24 リハ準備 |

合計 1〜2 時間想定。

#### C. 据置決定（次セッション以降も触らない）

以下 7 件は §2「デザイン適用 + UX 微改善」セクションの「据置」枠で判断済。**再議論禁止**（蒸し返すと CLAUDE.md §4「精度向上のための過剰実装は入れない」と整合性が崩れる）。

A1（スコア式）/ B2（並び順）/ B3（ルート表示の累計時間・地図）/ C1（予測精度）/ E1（カードに ✓ 消化済みボタン）/ E2（乗った一括クリア）/ E4（途中入園 sim 拡張）

### 仕様見直しの候補リスト【歴史記録 / 5/21 で全件処理済】

> **状態の最新は §2「デザイン適用 + UX 微改善」セクションを参照**。下記は当時の検討材料と意図の記録。
> 各項目の現状は: **✅ = 実装済 / 🕒 = 情報待ち / 📦 = 据置決定**。

| ID | 状態 | コミット or トリガ |
|---|---|---|
| A1 スコア式 | 📦 据置 | 来園日に実走してから判断 |
| A2 priority=0 矛盾 | ✅ 実装済 | `ea41e0b` |
| B1 DPA 警告位置 | 🕒 情報待ち | 5/18 営業時間発表後 |
| B2 並び順 | 📦 据置 | 21 件なら現状で十分 |
| B3 ルート表示拡張 | 📦 据置 | カード化（`3f6efb8`）で v1 は満足ライン |
| B4 食事初期値 | 🕒 情報待ち | 5/18 営業時間発表後 |
| B5 unvisited_musts 名前表示 | ✅ 実装済 | `ea41e0b` |
| C1 予測精度 | 📦 据置 | 仕様。当日 2-3 回再生成でカバー |
| C2 `get_time_factor` ガード | ✅ 実装済 | `bc42e73` |
| D1 dummy snapshot 整備 | 🕒 情報待ち | 5/23-24 リハ準備 |
| D2 `requires_reservation` 再確認 | 🕒 情報待ち | 5/24 リハ時 |
| E1 カードに「✓ 消化済み」 | 📦 据置 | 「乗った」と機能重複 |
| E2 「乗った」一括クリア | 📦 据置 | 既存リセットでカバー |
| E3 「⟳ いま」ボタン | ✅ 実装済 | `ea41e0b` |
| E4 sim に途中入園拡張 | 📦 据置 | 役割重複（lessons #18） |
| F1 確認ダイアログ赤化 | ✅ 実装済 | `3f6efb8` |

下記は「動かしてみて気になったこと」+ Phase 5/6 で意図的に見送った改善余地。優先度は東郷さんと話し合って決めた（記録のため残す）。

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
- **#18 役割重複の解消は別モード追加で済むことが多い**（5/21 当日モードの実運用対応時）
- **#19 Streamlit の widget 内部 state は `del session_state[key]` では消えない**（5/21 リセット機能修正時）
- **#20 CSS 修正が視覚的に効かない時は computed style で実態を確認**（5/21 caret-color 縦線が消えなかった件）
- **#21 多論点の未コミット作業を分割するには `git apply --cached --unidiff-zero`**（5/21 theme + 5 件を 3 コミットに分割した時）

### 残り Phase スケジュール

- 5/20 水 → **Phase 5 + 6 完了**
- 5/21 木 → **シミュ + リセット + 当日モード実運用 + デザイン適用 + UX 微改善 5 件 完了**
- 5/22 金 → Phase 7（デプロイ）着手予定 + 5/18 営業時間が出ていれば B1/B4
- 5/23 土 → Phase 7 完了 + リハーサル準備（D1: 朝昼夜 dummy）
- 5/24 日 → リハーサル（D2: requires_reservation 再確認 / 実 API 再確認）+ 予備日
- 5/25 月 → 来園日（実走、当日モードで 2-3 回再生成）

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
ディズニーランドのルート生成ツール、機能・デザイン・UX ともに完成（テスト 59/59 PASS、37 コミット、Theme Park Warm UI 適用済）。
今日は Phase 7（デプロイ）を進めたい。

PROGRESS.md §3 A の 3 タスク（Task 26 = requirements.txt + README / Task 27 = GitHub repo + Streamlit Cloud / Task 28 = デプロイ後動作確認）の手順を整理してください。GitHub の用語（PR / branch / remote / fork 等）は東郷さんが不慣れなので省略せず展開する（lessons #4）。

事前に `.venv/bin/pytest -q` で **59/59 PASS** + `.venv/bin/streamlit run app.py` で UI が起動して theme.py のアイボリー背景 + オレンジボタン + カード型ルートが反映されていることを目視確認してください。
```

### 引き継ぎチェックリスト（次セッション冒頭で確認すること）

- [ ] `git log --oneline -10` で最近のコミット（`ea41e0b / bc42e73 / 3f6efb8` 5/21 夜の 3 件、`6c49c5a` 過去ブロック修正 など）が見えること
- [ ] `git status` でクリーン（`theme.py` / `.streamlit/config.toml` がコミット済で untracked ではないこと）
- [ ] `.venv/bin/pytest -q` で **59 passed**
- [ ] `.venv/bin/streamlit run app.py` で UI が起動し、**Theme Park Warm**（アイボリー背景 #FFF8F0 / オレンジボタン #D85A30 / カード型ルート）が反映されていること
- [ ] CLAUDE.md / lessons.md（**#17〜#21** を含む）/ PROGRESS.md §2 末尾「デザイン適用」セクション + §3 A を読んで、次の主題（Phase 7）と情報待ち枠を把握
- [ ] **Phase 7 着手前**に Task 26-28 の手順をプレゼンしてから実装に入る（いきなり requirements.txt や README を書き始めない）

### 仕様見直しを進めるときの注意

1. **論点は独立**: 1 つずつ「ブレインストーミング → 合意 → 実装 → 確認」のサイクルで進める。複数同時改修は避ける（lessons.md #13）
2. **CSS 適用は localStorage との相性を確認**: Streamlit の rerun で CSS が再適用されることを確認、フォーカス・サイズ変動で UX を壊さないこと
3. **UI 改修は streamlit リロードで都度確認**: 単独テストではカバーしきれない見た目の確認が必要
4. **「来園日に実用できるか」が最終判定基準**: 過剰実装は捨てる。CLAUDE.md §4「精度向上のための過剰実装は入れない」を守る
5. **CSS 適用が崩れた時の戻し方を確保**: 1 改修 1 コミットで、見た目バグはすぐ revert できる粒度に
