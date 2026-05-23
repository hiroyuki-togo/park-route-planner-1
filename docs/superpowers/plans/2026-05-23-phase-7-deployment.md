# TDL Route Planner — Phase 7 (Deployment) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TDL Route Planner を Streamlit Community Cloud にデプロイし、来園日 2026-05-25 にスマホ Safari から実運用できる状態にする。最重要検証ポイントは **Queue-Times.com の集約 API が Streamlit Cloud（AWS US-East 想定）の IP から叩けること**。

**Architecture:** ローカルの git リポジトリを GitHub の public repo に push し、Streamlit Community Cloud と連携して自動デプロイ。デプロイ artifact は `requirements.txt` + `README.md` + 既存の `.streamlit/config.toml` の 3 点で完結する想定。コード本体（`src/`, `app.py`, `theme.py`, `data/`）への変更は基本的に発生させない。

**Tech Stack:** GitHub (gh CLI) / Streamlit Community Cloud（無料枠 = public repo 必須）/ Python 3.11 / 既存依存（streamlit, requests, pydantic, geopy, pandas, streamlit-local-storage）

---

## 前提・制約

- **個人利用限定・非商用**（CLAUDE.md §2）。リポジトリ名・README・UI 文言いずれにも Disney / TDL / OLC の商標は使わない
- 同行者は URL 共有による閲覧のみ（v1 では認証なし、誰でもアクセス可で OK）
- Streamlit Cloud 無料枠の制約：**public repo のみ**、コンテナ再起動でファイルシステムがリセット（`data/snapshots/` の永続化は v1 では行わない方針 = CLAUDE.md §5）

## 重要な分岐点（事前合意必要）

A. **リポジトリ名**：商標回避のため候補 3 つ（東郷さんが Task 27 Step 2 で選択）
- `route-planner-personal`
- `park-day-planner`
- `theme-park-route-planner-personal`

B. **Queue-Times が Cloud 側 IP からブロックされた場合の方針**（Task 28 で発覚した場合）
- (a) User-Agent 偽装で再試行（軽い対応）
- (b) 当日は東郷さんの iPhone で別途 Queue-Times を開いて JSON コピペ → アプリの「手動貼り付け」入力欄に流す（要追加実装、30 分〜1 時間）
- (c) 当日は dummy snapshot + シミュ予測のみで運用（最低限の妥協）

事前にどれを許容するか合意しておくと、当日トラブル時の判断が早い。

---

## File Structure

| 種別 | パス | 役割 |
|---|---|---|
| Create | `requirements.txt` | Streamlit Cloud が読む runtime 依存（pyproject.toml と別管理、scripts 専用依存は除外） |
| Create | `README.md` | プロジェクト概要・免責・起動方法・Queue-Times クレジット |
| Create | `runtime.txt` | Python 3.11 を Streamlit Cloud に明示（Heroku 互換フォーマット） |
| Verify | `.streamlit/config.toml` | 既存テーマがクラウドで反映されること |
| Verify | `.gitignore` | `.venv/` / `data/snapshots/` / `.env` が除外済 |

---

## Task 26: デプロイ artifact の作成（requirements.txt / README.md / runtime.txt）

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `runtime.txt`

このタスクはローカルで完結する。GitHub には次の Task 27 で push する。

### Step 1: 現在の runtime 依存と script 専用依存を切り分ける

実態調査の結果（5/23 セッション）:

| パッケージ | アプリ本体（`src/`, `app.py`） | scripts/ | 結論 |
|---|---|---|---|
| streamlit | ✅ | - | runtime 必須 |
| requests | ✅ | ✅ | runtime 必須 |
| pydantic | ✅ | - | runtime 必須 |
| geopy | ✅ | - | runtime 必須 |
| pandas | ✅ | - | runtime 必須 |
| streamlit-local-storage | ✅ | - | runtime 必須 |
| beautifulsoup4 | ❌ | ✅ (1 ファイル) | requirements.txt から **除外** |
| openpyxl | ❌ | ✅ (2 ファイル) | requirements.txt から **除外** |

Run（確認のみ、書き換えはしない）:
```bash
grep -rn "from bs4\|import bs4\|BeautifulSoup\|import openpyxl\|from openpyxl" src/ app.py
```
Expected: 何も出ない（アプリ本体での未使用を確認）

### Step 2: requirements.txt を作成

Create `requirements.txt`:
```
streamlit>=1.36
requests>=2.32
pydantic>=2.7
geopy>=2.4
pandas>=2.2
streamlit-local-storage>=0.0.21
```

⚠️ バージョンレンジは pyproject.toml と完全一致させる（lower bound のみ指定）。Streamlit Cloud に解決を委ねる。

### Step 3: 新規仮想環境で install 検証

```bash
python3.11 -m venv .venv-check
.venv-check/bin/pip install --quiet -r requirements.txt
.venv-check/bin/python -c "import streamlit, requests, pydantic, geopy, pandas, streamlit_local_storage; print('OK')"
rm -rf .venv-check
```
Expected: `OK` が出る、pip エラーなし

### Step 4: runtime.txt を作成

Create `runtime.txt`:
```
python-3.11
```

Streamlit Cloud は (a) ダッシュボードの Advanced settings、または (b) `runtime.txt` で Python バージョンを指定できる。両方併用する（フォーマットが Heroku 互換、`python-3.11` のように記述）。

### Step 5: README.md を作成

Create `README.md`:
````markdown
# Route Planner (Personal Tool)

個人の遊園地来園日に使う、ルート自動生成ツールの試作。
**個人学習目的・非商用利用限定**。

## 概要

- ライブ待ち時間データ（[Queue-Times.com](https://queue-times.com/) の集約 API、5 分毎更新）からアトラクション巡回ルートを生成
- 「必ず乗る」「優先度」「DPA 予約済」「食事」「ショー観賞」を入力 → 待ち時間予測 + 移動距離込みで最適化
- 当日モード（現在時刻からインクリメンタル再生成）/ シミュレーションモード（前日叩き台）の 2 モード搭載

## 起動方法（ローカル）

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

ブラウザで `http://localhost:8501` を開く。

## 技術スタック

Python 3.11 / Streamlit / requests / Pydantic / geopy / pandas

## データソース

待ち時間データは [Queue-Times.com](https://queue-times.com/) の集約 API（park_id=274）から取得。
**Powered by Queue-Times.com**

## 免責事項

- 本ツールは個人の学習目的で作成された試作です
- 商用利用・再配布は禁止
- 本ツールに含まれる固有名詞・地名等は、すべて個人の利用記録の便宜上のもので、いかなる法人・サービスとも無関係です
- 待ち時間予測の精度は保証しません。実走時に必ず公式情報を参照してください

## ライセンス

All rights reserved.（個人利用前提のため、オープンソースライセンスは付与しません。コードのコピー・再配布は禁止）
````

⚠️ Disney / TDL / OLC / Tokyo Disney 等の商標は README 本文に**書かない**。「遊園地」「テーマパーク」等の一般語で記述。

### Step 6: pytest でローカル健全性を再確認

```bash
.venv/bin/pytest -q
```
Expected: `64 passed`（artifact 追加はテスト数・実装に影響しない、念のため回帰確認）

⚠️ Streamlit の起動テストはここでは行わない。既に 8501 で稼働中の既存インスタンスを止める必要があり、東郷さんの作業中ブラウザを切断するリスクがある。artifact の install 検証は Step 3 で完結している。

### Step 7: コミット

```bash
git add requirements.txt README.md runtime.txt
git status   # 上記 3 ファイルのみ staged であることを確認
git commit -m "feat: add deployment artifacts (requirements.txt / README.md / runtime.txt) for Streamlit Cloud"
```

Expected: 1 commit が main に積まれる。`git log --oneline -3` で確認。

---

## Task 27: GitHub repo 作成 + Streamlit Community Cloud デプロイ

このタスクは **東郷さんと並走で進める**（GitHub 用語が初出、Streamlit Cloud は GUI 操作）。各ステップで用語を展開する。

**Files:** （コード変更なし）

### Step 1: gh CLI の認証状況を確認

> 用語:
> - **gh CLI**: GitHub の公式コマンドラインツール。ブラウザを開かなくてもリポジトリ作成・push ができる
> - **認証 (auth)**: GitHub に「この PC からの操作は togo-hiroyuki 本人が許可している」と証明する仕組み

```bash
gh auth status
```
Expected: `Logged in to github.com account togo-hiroyuki` などのアカウント名表示

未認証の場合:
```bash
gh auth login
```
- プロンプトで `GitHub.com` → `HTTPS` → `Login with a web browser` を選択
- 表示される 8 桁コードをブラウザでコピペ（パスワード入力不要）

### Step 2: リポジトリ名を東郷さんに確定してもらう

候補 3 案（CLAUDE.md §2 商標回避）:

| 候補 | ニュアンス |
|---|---|
| `route-planner-personal` | 短い・汎用的 |
| `park-day-planner` | 「来園日プランナー」感が出る |
| `theme-park-route-planner-personal` | 説明的だが長い |

東郷さんが選んだ名前を以下の `<REPO_NAME>` プレースホルダに置く。

### Step 3: GitHub にリモートリポジトリを作成

> 用語:
> - **リポジトリ (repository / repo)**: GitHub 上のプロジェクト保管庫
> - **public**: 誰でも閲覧可能。Streamlit Cloud 無料枠は public 必須（CLAUDE.md §5）
> - **remote**: ローカルの git が push する先の宛先。今回は `origin` という別名で GitHub を指す
> - **--source=.**: 「カレントディレクトリの .git をこのリポジトリと紐付ける」設定

```bash
gh repo create <REPO_NAME> --public --source=. --remote=origin --description "個人学習目的のルート自動生成ツール（非商用）"
```
Expected: `✓ Created repository togo-hiroyuki/<REPO_NAME> on GitHub`

⚠️ `--push` フラグは**付けない**。次ステップで明示 push する（失敗時の切り分けがしやすい）。

### Step 4: main ブランチを GitHub に push

> 用語:
> - **push**: ローカルのコミットを GitHub に送る操作
> - **branch**: コミットの一本道。今は `main` だけ
> - **-u (--set-upstream)**: ローカルの `main` が GitHub の `main` を追跡するように紐付け。次回以降は `git push` だけで OK

```bash
git push -u origin main
```
Expected:
```
Enumerating objects: ...
To https://github.com/togo-hiroyuki/<REPO_NAME>.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

### Step 5: ブラウザで repo の中身を目視確認

```bash
gh repo view --web
```
これでデフォルトブラウザに repo ページが開く。

確認ポイント:
- [ ] README.md が表示される
- [ ] `app.py` / `requirements.txt` / `runtime.txt` / `src/` / `data/` が見える
- [ ] `.venv/` / `data/snapshots/` / `.env` は**見えない**（.gitignore が効いている）
- [ ] コミット数 = ローカルの `git log --oneline | wc -l` と一致

### Step 6: Streamlit Community Cloud にサインイン

ブラウザで <https://share.streamlit.io> にアクセス:

1. 「Sign in」→「Continue with GitHub」
2. togo-hiroyuki アカウントで認証
3. リポジトリアクセス許可を求められたら **「Only select repositories」**を選び、新規作成した `<REPO_NAME>` だけを許可（他の repo を巻き込まない）

### Step 7: 新規アプリのデプロイ設定

ダッシュボードで「Create app」→「Deploy a public app from GitHub」を選択し、以下を入力:

| 項目 | 値 |
|---|---|
| Repository | `togo-hiroyuki/<REPO_NAME>` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL (custom subdomain) | 任意。空白可（ランダム subdomain が振られる） |
| **Advanced settings** | 開く |
| Python version | `3.11` |
| Secrets (TOML 形式) | （何も入れない。Queue-Times は認証不要） |

「Deploy!」を押す → ビルドが開始される（5-10 分）。

### Step 8: ビルドログ確認

デプロイ画面でログを観察:
- [ ] `Installing dependencies from requirements.txt` 行が出る
- [ ] 6 パッケージすべてが `Successfully installed` で着地
- [ ] `Starting Streamlit server` 行 → 最終的に `You can now view your Streamlit app in your browser.`
- [ ] 赤い ERROR 行が**ない**

エラーが出たら**停止**してログを東郷さんに共有 → 原因を切り分けてから再デプロイ。
特に警戒ポイント: `streamlit-local-storage` の依存解決失敗（古いバージョンで Streamlit 互換性が崩れる事例あり）。

### Step 9: デプロイ URL を開く

`https://<app-name>.streamlit.app` にアクセスしてホーム画面が表示されることを確認。

### Step 10: README にデプロイ URL を追記してコミット

`README.md` の「## 概要」セクション下に以下を追加:

```markdown
## デプロイ URL

<https://<app-name>.streamlit.app>

⚠️ 個人利用前提のため、URL の SNS 拡散等はご遠慮ください。
```

```bash
git add README.md
git commit -m "docs: add deployment URL to README"
git push
```
Expected: Streamlit Cloud が GitHub の更新を検知して自動再デプロイ（1-2 分）

---

## Task 28: デプロイ環境での動作確認（最重要 = Queue-Times 検証）

このタスクは **「クラウド側 IP から Queue-Times.com が叩けるか」が PASS/FAIL の最重要分岐**。失敗時は事前合意した分岐方針（前述「重要な分岐点 B」）に沿って判断。

**Files:** （コード変更なし、東郷さんの目視確認 + Streamlit Cloud ダッシュボードのログ確認）

### Step 1: 当日モード — Queue-Times 実データ取得

デプロイ URL を東郷さんの **iPhone Safari** で開く（来園日と同じ環境で確認するため）。

操作:
1. モード = 「**当日モード**」を選択
2. 「🔄 待ち時間を取得（Queue-Times 経由）」ボタンを押す

✅ 期待:
- [ ] `last_updated` に**当日の JST 時刻**（例: 11:30）が表示
- [ ] 美女と野獣の `wait_min` が現実的な値（例: 80-150 分）
- [ ] フッターに「Powered by [Queue-Times.com](https://queue-times.com/)」リンクが見える
- [ ] queue_times_id null の `buzz` / `minnie_style` 行に「⚠️ ライブ取得対象外」注記（buzz は 5/22 削除済なので minnie_style のみ）
- [ ] 「古いデータ警告」が出ない（Queue-Times のタイムスタンプが直近 5-10 分以内）

### Step 2: もし Queue-Times が取れなかった場合の切り分け

UI に「取得に失敗しました、シミュ snapshot にフォールバックします」が出た場合:

Streamlit Cloud ダッシュボードで `Manage app` → ログタブを開き、以下を grep:
- `fetch_realtime_wait_times` の例外
- `requests.exceptions.*` のスタックトレース
- HTTP ステータスコード（403 / 503 / Connection reset / Timeout のどれか）

可能なら、ダッシュボードの「Reboot app」横の Python REPL（提供されていれば）で:
```python
import requests
r = requests.get("https://queue-times.com/parks/274/queue_times.json", timeout=10,
                 headers={"User-Agent": "Mozilla/5.0"})
print(r.status_code, len(r.content))
```
Expected: `200 <数千バイト>`

切り分け結果に応じて分岐:
- **(a) 200 OK だがパースで落ちる** → ローカルと同じはず。`src/scraper.py` の例外箇所を特定して fix
- **(b) 403/503 で UA 起因の可能性** → `src/scraper.py` の `requests.get()` に Chrome UA を渡す（軽い対応、追加 10 分）
- **(c) Connection reset / timeout = Cloud IP がブロック** → 事前合意 B の (b)/(c) パスへ

### Step 3: シミュレーションモード — 5/25 ルート生成

操作:
1. モード = 「**シミュレーション**」
2. 日付 = `2026-05-25` を選択
3. アトラクション設定で「必ず乗る」を 2-3 件選ぶ（例: 美女と野獣 / モンスターズ・インク）
4. 「ルートを生成」を押す

✅ 期待:
- [ ] ルートカードが時系列順に並ぶ
- [ ] 各カードに「待ち●分 ・ 体験●分 ・ → 終了時刻」が表示（5/22 の `2632a40` 修正分）
- [ ] DPA 未予約警告 / 食事ブロック / ショーブロックが正しい時刻に挟まる

### Step 4: テーマ（Theme Park Warm）の反映確認

✅ 期待:
- [ ] 背景がアイボリー（`#FFF8F0`）
- [ ] 強調色がオレンジ（`#D85A30`）— スライダーのトラック、ラジオの選択ドット、checkbox の塗り
- [ ] ルートカードが横並び、丸枠（theme.py の `render_route_step()`）
- [ ] 「はい、リセット」確認ボタンだけが**赤塗り**（5/21 の `3f6efb8` F1 対応）

⚠️ クラウド側で `.streamlit/config.toml` が認識されない場合、`primaryColor` だけデフォルト赤に戻る可能性あり。theme.py の CSS インジェクションは別系統なので、レイアウト・カードは効くはず。スクショで東郷さんに目視確認してもらう。

### Step 5: localStorage 永続化

操作:
1. 「必ず乗る」を 3 件チェック
2. ブラウザ更新（Cmd+R / iPhone は引っ張って更新）
3. チェック状態が復元されていれば ✅
4. 「🧹 セッションリセット」→ 2 段階確認 → 状態が初期化、リロードで localStorage から復元
5. 「🗑 完全リセット」→ 2 段階確認 → 状態が初期化、リロードしても空のまま

### Step 6: iPhone Safari での操作感確認（来園日リハ）

iPhone Safari で開いて:
- [ ] 文字サイズ・ボタンサイズが指で押せる
- [ ] アトラクション 21 件のスライダー操作が詰まらない
- [ ] ルートカードのスクロールがスムーズ
- [ ] 「ルートを生成」が 3 秒以内に完了

⚠️ Streamlit のモバイル UI は「ハンバーガーメニュー（左上 3 本線）にサイドバーが折り畳まれる」想定。サイドバーがある実装になっていれば、開閉が指でできることを確認。

### Step 7: ドキュメント更新 & 引き継ぎコミット

`PROGRESS.md` を更新（§1「現在のステータス」を Phase 7 完了に書き換え、§3 から完了タスクを移動）。
新たに学んだことがあれば `lessons.md` #28〜 に追記。

```bash
git add PROGRESS.md lessons.md
git commit -m "docs: Phase 7 deployment complete + lessons from deploy session"
git push
```
Expected: Streamlit Cloud が再デプロイ（README 等のみなのでビルド時間 1 分以内）

---

## 完了の DoD（Definition of Done）

Phase 7 完了の条件:

- [ ] デプロイ URL が iPhone Safari で開ける
- [ ] 当日モードで Queue-Times の実データ取得が動く **OR** 動かない場合の代替パスが東郷さんと合意済み
- [ ] シミュレーションモードでルートが正しく生成される
- [ ] テーマが反映されている（アイボリー背景 + オレンジ強調）
- [ ] localStorage の永続化・リセットが動く
- [ ] PROGRESS.md / lessons.md に Phase 7 セッションメモが残っている
- [ ] `git status` がクリーン、`main` が `origin/main` と同期

---

## 想定工数

| Task | 想定時間 | 並走可否 |
|---|---|---|
| Task 26（artifact 作成） | 30 分〜1 時間 | Claude 単独可 |
| Task 27（GitHub + Streamlit Cloud） | 1〜1.5 時間 | 東郷さんと並走必須（GUI 操作） |
| Task 28（動作確認） | 30 分〜1 時間 | 東郷さんと並走（iPhone 目視） |

**合計: 2〜3.5 時間**。5/23 中に Task 26-27 を終え、5/24 に Task 28 + リハーサルを当てるのが余裕がある進め方。

---

## リスクと対策

| リスク | 確率 | 影響 | 対策 |
|---|---|---|---|
| Queue-Times が Cloud IP からブロック | 中 | 高 | 事前合意 B、UA 偽装 / 手動コピペ / dummy フォールバック |
| `streamlit-local-storage` の依存解決失敗 | 低 | 高 | バージョン明示、最悪 localStorage 機能を一時切る |
| `.streamlit/config.toml` の primaryColor が無視される | 低 | 低 | theme.py の CSS で大部分はカバー、見た目劣化のみ |
| Python 3.11 が Cloud で選べない | 低 | 中 | runtime.txt + Advanced settings の二重指定 |
| ビルドが 10 分以上かかる | 低 | 低 | 待つ。requirements.txt が小さいので発生確率低 |

---

## 参照

- [プロジェクト指示書](../../CLAUDE.md)
- [仕様書](../specs/2026-05-16-tdl-route-planner-design.md)
- [Phase 1-6 実装計画](2026-05-16-tdl-route-planner.md)
- [進捗ハンドオフ](../../PROGRESS.md)
- [教訓集](../../lessons.md)（特に #4 GitHub 用語、#22-24 Queue-Times 経緯）
