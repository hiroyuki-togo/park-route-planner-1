# TDL Route Planner — 進捗ハンドオフ

> 次セッションの Claude Code が状況を即時把握するための引き継ぎファイル。

**最終更新**: 2026-05-23（sim 時刻軸拡張完了後）
**来園日**: 2026-05-25（月）
**残り日数**: 3 日

---

## 1. 現在のステータス

**Phase 1〜6 完了 + シミュ + 当日モード実運用 + デザイン適用 + UX 微改善 + ライブ取得復活 + 後続改善 完了**。
**テスト 69/69 PASS**、Streamlit 起動確認済 + 東郷さん目視確認済（複数回）。

5/22 1 日で本日累計 **13 コミット** 進めた:

| 主題 | コミット |
|---|---|
| ルートカード体験時間表示 + 徒歩係数 2.0 km/h | `4f56200` / `2632a40` |
| Queue-Times.com 採用（OLC WAF 黙殺対応、5 段階 Phase A-E） | `5900440` / `7ab57e4` / `4a5e37b` / `576bee7` / `51f0722` |
| 未収録アトラクション注記の位置修正 | `b249c6b` |
| buzz（2024 クローズ済）削除 + minnie_style マッピング修正 | `208862d` |
| TZ バグ修正（UTC→JST）+ 閉園時警告 | `8d7db19` |
| シミュ精度向上（Queue-Times stats 平均値、美女と野獣 20→74 分等） | `dbe5421` |
| UI 3 件修正（TZ 二重変換 / localStorage zombie / 古いデータ警告） | `ef7b19f` |
| モード切替で route+snapshot をクリア（sim/live 別軸化） | `ea5f37f` |

今日発覚 → 解決した最大トピック: **アプリ史上「ライブ取得が動いている」と認識していたが、実態は dummy snapshot にずっとフォールバックしていただけ**（lessons #22）。原因は OLC 公式 API が WAF で curl/requests を完全黙殺する仕様変更（lessons #23）。第三者の集約 API **Queue-Times.com** に切り替えて 5 分毎更新の実データ取得を実現（lessons #24）。

**5/23 セッション**: シミュレーションモードの時刻軸拡張を実装（Phase 7 デプロイ前の追加機能、東郷さん要求）。
任意時刻スタート + 「現在時刻 / 現在位置 / 乗った」UI を sim でも開放、wait_min は β 計算式（下限 0.9）で時刻補正。
詳細は [docs/superpowers/specs/2026-05-23-sim-time-axis-design.md](docs/superpowers/specs/2026-05-23-sim-time-axis-design.md) と [plans/2026-05-23-sim-time-axis.md](docs/superpowers/plans/2026-05-23-sim-time-axis.md)。
テスト 64 → 69 PASS。次は Phase 7（デプロイ）。

残るは **Phase 7（デプロイ、5/23-24 目標）**。

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

### ライブ取得を Queue-Times.com 経由に切替（第一命題復活） — 5/22 完了

5/22 セッションで発覚した事実: アプリ史上ライブ取得は一度も成功しておらず、`fetch_realtime_wait_times()` の except 分岐が常に `2026-05-20_1628_dummy.json` を返していただけだった（UI には毎回「取得成功：16:28」と表示されていたため誤認）。原因は OLC が curl/requests を TLS 指紋で完全黙殺する WAF を導入したこと + 待ち時間ページ自体の公開停止（iPhone Safari → `calendar.html` リダイレクト）。

**選択肢の網羅検討** → Queue-Times.com の集約 API（park_id=274、無料、認証不要、5 分毎更新）が実用可能と確認。東郷さんの iPhone Safari からも JSON 取得成功、Mac 側 curl も 0.28 秒で 200 OK。19/21 件のマッピング完了（buzz / minnie_style は Queue-Times 未収録、null 運用）。

| コミット | 内容 |
|---|---|
| `5900440` | **Phase A**: data/attractions.json に queue_times_id 21 件 + src/models.py に Attraction.queue_times_id / WaitTimeEntry.queue_times_id |
| `7ab57e4` | **Phase B**: src/scraper.py を Queue-Times パース・ID マッチ・5 分実キャッシュに全書換 + tests/fixtures/queue_times_sample.json 新規 + test_scraper.py 12 件 PASS |
| `4a5e37b` | **Phase C**: src/constants.py に OPENING_BASE_WAIT_BY_TIER 移動、src/router.py で queue_times_id null は予測値代用、conftest 更新、test_router 新規 1 件追加（13 PASS） |
| `576bee7` | **Phase D**: app.py 取得ボタンラベル変更、JST 表示、Queue-Times 失敗時シミュ snapshot 自動フォールバック、queue_times_id null 行に「⚠️ 予測値」注記、フッターに「Powered by Queue-Times.com」常時表示 |
| (このコミット) | **Phase E (docs)**: CLAUDE.md §2 / 仕様書 §1.2 §4 / lessons.md #22-24 / PROGRESS.md 更新 |

**動作確認** (東郷さん側):
- [ ] Streamlit 再起動後、当日モード → 「🔄 待ち時間を取得（Queue-Times 経由）」で実データが取れる（last_updated が今日の時刻）
- [ ] 美女と野獣の wait_min が当日実値（例: 140 分）でルートに反映される
- [ ] アトラクション設定の buzz / minnie_style 行に「⚠️ ライブ取得対象外」注記が出る
- [ ] フッターに「Powered by Queue-Times.com」のクレジットリンクが見える

---

### ルートカード表示拡張 + 徒歩係数調整 — 5/22 完了

| コミット | 内容 |
|---|---|
| `4f56200` | **徒歩係数調整**: PARK_FACTOR_NORMAL 1.4→2.0、RAIN 1.7→2.3（家族 6 人 + 2 歳児 + ベビーカー想定で実効 2.0 km/h） |
| `2632a40` | **ルートカード表示**: 待ち時間 > 0 のとき体験時間が elif で隠れていた問題を修正。attraction/dpa は「待ち15分 ・ 体験3分 ・ → 09:52 終了」フル表示、meal/show/parade は「90分 ・ → 13:30 終了」表示 |

---

### シミュレーションモード時刻軸拡張（sim ≒ 当日モードの合成版） — 5/23 完了

東郷さん要求「シミュにも時間の概念を入れたい」を受けて、sim モードを「9:00 開園固定」から「任意時刻スタート + 時刻別補正された合成 snapshot」に拡張。あわせて「現在時刻 / 現在位置 / 乗った」UI を sim にも開放し、当日モードとの UI 差分を最小化（is_sim_mode 分岐が 3 段削減）。

仕様: [docs/superpowers/specs/2026-05-23-sim-time-axis-design.md](docs/superpowers/specs/2026-05-23-sim-time-axis-design.md)
プラン: [docs/superpowers/plans/2026-05-23-sim-time-axis.md](docs/superpowers/plans/2026-05-23-sim-time-axis.md)

Subagent-Driven Development で 9 Task を実装。各タスクで spec 適合性レビュー + コード品質レビューの 2 段階を通過。テスト 64 → **69 PASS**。

| Task | コミット | 内容 |
|---|---|---|
| 1 | `d2fa4ae` | `TIME_FACTOR_FLOOR = 0.9` / `TIME_FACTOR_AVG_EFFECTIVE = 13.1/12` 追加 |
| 2 | `3a3f9e9` | `build_snapshot_at(attractions, target_datetime)` 実装（β 計算式: `wait = baseline × max(0.9, factor) / 1.09`）|
| 3 | `abd0b4e` | 既存 6 テストを `test_snapshot_at_*` に置換 + 期待値を β 計算式に合わせる |
| 4 | `637a68e` | 新規 3 テスト（時刻別 / 下限保護 / null フォールバック） |
| 5 | `b29e93e` | `test_simulate_then_route_at_arbitrary_time` に 11:00 スタート版で書き換え |
| 6 | `09dce50` | app.py の `build_opening_snapshot` 呼び出し 2 箇所を `build_snapshot_at(attractions, datetime.combine(route_date, current_time_val))` に置換（UI 変更なし）|
| 7a | `38ed43e` | sim mode で「現在時刻 / 現在位置」UI 開放 + 開園前/閉園後警告を sim にも適用 + "9:00 開園想定" メッセージを動的化 |
| 7b | `61b20c1` | sim mode で「乗った」UI 開放（3 カラム化）+ router 呼び出しの `visited` を sim でも渡す |
| 7b-fix | `b8fbaa7` | mode 切替時に `visited_attractions` をクリア（sim/live で意味論が違うため、ゾンビ参照防止）|
| 8 | `2dbc3f0` | 旧 `build_opening_snapshot` を `src/simulator.py` から削除（grep 0 件確認） |
| 9 | `4917711` / `f5cedec` | PROGRESS.md / lessons.md 更新 + scripts docstring 修正 + ヘッダー日付・テスト数の bump |

**設計の主要判断**:

1. **役割重複を allow する判断**（lessons #18 への反転追記）: sim/live モードを「データソースだけが違う双子」として統合。旧仕様の「役割を分けるために sim を制限する」より、「重複を allow して UI コード分岐を削減する」を採用
2. **β 計算式の下限 0.9**: `effective_factor = max(0.9, get_time_factor(hour))` で朝・夜の極端を抑える。「営業時間中、最も空いてる時間帯でも avg の 82% は並ぶ」という観察則の実装
3. **wait_min 検算例**: 美女と野獣 (avg=74) → 9:00 で 61 分 / 11:00 で 88 分 / 15:00 で 81 分 / 20:00 で 61 分（下限保護）

**副作用**: 現状 sim mode（9:00 開園想定）の予測値が変わる（美女と野獣 74 → 61 分）。これは「朝開園直後は実際少し空いている」を反映する仕様変更で、5/24 リハで Queue-Times 実値と比較して下限値（0.9）を微調整する余地あり。

---

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

**前提**: 5/23 中に「シミュ時刻軸拡張」が完了済（[plans/2026-05-23-sim-time-axis.md](docs/superpowers/plans/2026-05-23-sim-time-axis.md)）。
このタスクはその次のステップとして実施。

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

### ライブ API のレート制限 → **5/22 解消**

旧仕様: OLC 公式 `/_/realtime/tdl_attraction.json` を直叩き → 「レート制限でタイムアウト」と認識していた。

5/22 セッションで実態判明: OLC が WAF を導入し、**curl/requests を TLS 指紋で完全黙殺**（Akamai の silent drop）。レート制限ではなく構造的に取得不可能な状態。Queue-Times.com（park_id=274）の集約 API に切替で **完全に解消**（5 分毎更新の実データ取得）。

詳細は lessons #22-24 / 仕様書 §4 / §2「デザイン適用」末尾の Queue-Times セクション参照。

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
ディズニーランドのルート生成ツール、機能完全 + sim 時刻軸拡張まで完了。
テスト 69/69 PASS、Theme Park Warm UI 適用済。残りは Phase 7（デプロイ）のみ。

来園日は 2026-05-25（月）。今日は 5/24（土曜）。残り 1 日でデプロイ + リハ。

着手済みプラン: docs/superpowers/plans/2026-05-23-phase-7-deployment.md
（Task 26 = requirements.txt + README / Task 27 = GitHub repo + Streamlit Cloud / Task 28 = デプロイ後動作確認）

事前に東郷さんと合意した方針:
- リポジトリ名: park-route-planner-1（"-1" の意図は東郷さんに確認）
- Queue-Times が Cloud IP からブロックされた場合: (a) UA 偽装等 30 分以内の軽い対応まで → ダメなら (c) シミュ妥協

プランをそのまま実行するか、見直しが要るかを確認してから着手してください。
GitHub の用語（PR / branch / remote / fork 等）は東郷さんが不慣れなので省略せず展開する（lessons #4）。
```

### 引き継ぎチェックリスト（次セッション冒頭で確認すること）

#### A. 環境・コード状態の健全性

- [ ] `git log --oneline -15` で 5/23 の sim 時刻軸関連コミット 12 個（`d2fa4ae` Task 1 から `f5cedec` Task 9 fix まで）が見えること
- [ ] `git status` でクリーン
- [ ] `.venv/bin/pytest -q` で **69 passed**
- [ ] `lsof -i :8501` / `lsof -i :8502` で前回セッションの Streamlit プロセスが残っていないか確認（残っていれば必要に応じて kill）

#### B. ドキュメントの把握

- [ ] [CLAUDE.md](CLAUDE.md) を読む
- [ ] [lessons.md](lessons.md) を読む（特に #4 GitHub 用語、#22〜#24 Queue-Times 経緯、#18 役割重複の追記）
- [ ] PROGRESS.md §1（現在のステータス、5/23 セッション末尾の追記含む） + §3 A（Phase 7 主題）を読む
- [ ] [docs/superpowers/specs/2026-05-23-sim-time-axis-design.md](docs/superpowers/specs/2026-05-23-sim-time-axis-design.md)（直近実装の仕様）を読む
- [ ] [docs/superpowers/plans/2026-05-23-phase-7-deployment.md](docs/superpowers/plans/2026-05-23-phase-7-deployment.md)（次に実行するプラン）を読む

#### C. アプリ動作の最終確認（5/24 当日リハ兼）

- [ ] `.venv/bin/streamlit run app.py` で UI 起動
- [ ] **当日モード**で「🔄 待ち時間を取得（Queue-Times 経由）」→ 5/24 当日の実値が出る
- [ ] **シミュモード**で時刻を 11:00 に変更 → wait_min が 9:00 より明らかに大きい（時刻補正が効いている証拠）
- [ ] sim ↔ 当日切替で「乗った」がクリアされる
- [ ] フッターに「Powered by Queue-Times.com」表示
- [ ] アトラクション設定の minnie_style 行に「⚠️ ライブ取得対象外」注記

#### D. Phase 7 着手前の判断

- [ ] Phase 7 プラン（plans/2026-05-23-phase-7-deployment.md）を東郷さんと一緒に再確認
- [ ] 「-1」サフィックスの意図確認 → リポジトリ名を確定
- [ ] **いきなり requirements.txt や README を書き始めない**（プラン手順を再プレゼンしてから着手）

### 仕様見直しを進めるときの注意

1. **論点は独立**: 1 つずつ「ブレインストーミング → 合意 → 実装 → 確認」のサイクルで進める。複数同時改修は避ける（lessons.md #13）
2. **CSS 適用は localStorage との相性を確認**: Streamlit の rerun で CSS が再適用されることを確認、フォーカス・サイズ変動で UX を壊さないこと
3. **UI 改修は streamlit リロードで都度確認**: 単独テストではカバーしきれない見た目の確認が必要
4. **「来園日に実用できるか」が最終判定基準**: 過剰実装は捨てる。CLAUDE.md §4「精度向上のための過剰実装は入れない」を守る
5. **CSS 適用が崩れた時の戻し方を確保**: 1 改修 1 コミットで、見た目バグはすぐ revert できる粒度に
