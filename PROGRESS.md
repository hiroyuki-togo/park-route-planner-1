# TDL Route Planner — 進捗ハンドオフ

> 次セッションの Claude Code が状況を即時把握するための引き継ぎファイル。

**最終更新**: 2026-05-17（Task 9-11 完了後）
**来園日**: 2026-05-25（月）
**残り日数**: 8 日

---

## 1. 現在のステータス

**Phase 1 + Phase 2 + Phase 3（コード側）完了**。12 コミット、テスト 24 件中 22 PASS / 2 FAIL（FAIL は人力作業待ちの意図的なもの）。
プラン §10 想定スケジュールに対して **1 日先行**。

---

## 2. 完了済みタスク（Task 1〜11）

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
| 11 | `tests/test_masters.py`（妥当性検証、6 件中 2 件は座標埋め完了まで意図的 FAIL） | `4bc25ed` |

---

## 3. 次にやること

### Phase 3 完了の最終ピース：**東郷さんによる座標入力（人力、30〜40 分）**

Claude Code は代行不可。以下を実施：

1. Google マップで [data/attractions.json](data/attractions.json) の 21 件と [data/restaurants.json](data/restaurants.json) の 10 件、各入口を検索
2. 右クリック → 座標コピーで lat/lng を取得し、`null` を実数値で置換
3. 美女と野獣の `requires_reservation` が現状の運用と合っているか公式サイトで確認（変わっていれば修正）
4. 完了後 `.venv/bin/pytest tests/test_masters.py -v` を実行。全 6 PASS になれば Phase 3 完了

### その後：Task 12（Phase 4：距離計算 + 雨天モード）

`src/distance.py` の TDD 実装。プラン Task 12-15 を参照。

### 残り Phase スケジュール（プラン §10、1 日先行で更新）

- 5/18 月 → Phase 3 人力（座標入力） + Phase 4 着手（距離・予測）
- 5/19 火 → Phase 4 仕上げ + Phase 5 着手
- 5/20-21 水木 → Phase 5（ルート生成 TDD）
- 5/22-23 金土 → Phase 6（Streamlit UI）
- 5/24 日 → Phase 7（デプロイ）+ リハーサル
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
| `get_time_factor(21)` がフォールスルーで `1.0` を返す。閉園時刻のガード未実装 | Task 13（predictor）実装時に予測時刻が CLOSE_TIME を超えないことを呼び出し側で保証するか、関数内で ValueError を投げるか判断 |
| `pyproject.toml` に `beautifulsoup4` が残っているが scraper では未使用 | Phase 7 で `requirements.txt` 生成時に判断（残してもサイズ影響軽微） |
| `.claude/` ディレクトリが untracked のまま | 必要なら `.gitignore` に追記。今は無害 |

### ライブ API のレート制限

セッション最終確認で `fetch_realtime_wait_times()` の実 API 呼び出しが **タイムアウト** した。原因の可能性：

- Task 5 で 1.8MB HTML をダウンロードした直後の連続アクセス → IP ベースのレート制限
- アプリ側のキャッシュ（5 分 TTL）と無関係に、外側のネットワーク層で抑制された

**対処**：時間を置けば回復するはず。次回起動時に再確認すること。コードロジック上の問題ではない（オフラインテスト 20/20 PASS）。

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

**座標入力済みの場合：**
```
ディズニーランドのルート生成ツール、Phase 4 から続きをお願いします。
PROGRESS.md と CLAUDE.md を読んで状況を把握してから、まず `.venv/bin/pytest tests/test_masters.py -v` で Phase 3 完了を確認し、Task 12（距離計算）に着手してください。
```

**座標入力がまだの場合：**
```
ディズニーランドのルート生成ツール、進めます。
PROGRESS.md と CLAUDE.md を読んで状況を把握してから、Phase 4 の Task 12（距離計算 TDD）に着手してください。座標は仮値で OK、Phase 3 の人力部分は並行で進めます。
```
