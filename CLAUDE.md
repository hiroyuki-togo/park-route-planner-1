# TDL Route Planner — Project Instructions

東京ディズニーランド（TDL）来園日に使う、個人用のルート自動生成ツール。
このファイルは Claude Code が毎セッション参照する、プロジェクト固有の指示書。

---

## 1. 必ず参照するファイル

### セッション開始時に最初に読むもの（必須）

- [PROGRESS.md](PROGRESS.md) — **進捗ハンドオフ**。完了タスク・次の着手点・引き継ぎ判断・既知の課題が集約されている。**毎セッション冒頭で必ず Read すること**
- [lessons.md](lessons.md) — 過去の教訓・繰り返し回避すべきミス。短いので毎回読んでよい

### 必要に応じて参照するもの

- [docs/superpowers/plans/2026-05-16-tdl-route-planner.md](docs/superpowers/plans/2026-05-16-tdl-route-planner.md) — **実装計画**。次に着手する Task を確認するときに参照
- [docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md](docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md) — **実装仕様書（正本）**。設計判断の出典
- [memory.md](memory.md) — プロジェクトの意思決定経緯と背景
- [archive/ディズニープラン-TDS.md](archive/ディズニープラン-TDS.md) — TDS 向け旧版（参考のみ、追従不要）

### 運用ルール

- PROGRESS.md は **セッション完了時に更新** すること。次セッションへの引き継ぎを途切れさせない
- PROGRESS.md 本体は **「直近 2 週間＋進行中」のみ**。完了分は `PROGRESS_archive_YYYYQn.md` へ移し、冒頭ダイジェスト（📜 これまでの歩み）を維持する
- lessons.md は **東郷さんから指摘・修正を受けた / 想定外の事象が起きた** タイミングで追記
- 50 行を超えたら古い順に整理してスリム化（CLAUDE.md グローバル原則）

---

## 2. このプロジェクト固有の絶対ルール

- **個人利用限定**：公開・商用化なし。GitHub 公開する場合も「個人学習目的・商用利用不可」を明示
- **Disney / OLC 商標は成果物に使わない**（リポジトリ名・README・UI 文言いずれも）
- **待ち時間データは Queue-Times.com の集約 API 経由で取得**（OLC 公式は WAF が curl/requests を完全黙殺。5/22 確認・[lessons #23](lessons.md)）。Queue-Times の更新頻度は 5 分なので、アプリ側も 5 分キャッシュを実装済み。**「Powered by Queue-Times.com」のクレジット表示が必須**（[scraper.py](src/scraper.py) / app.py フッター）
- **公式アプリ API 解析・MyDisney ログイン経路には触れない**（規約違反濃厚で却下済み）
- **対象パークは TDL のみ**。TDS は v1 スコープ外（TDR 共通化は v2 以降で検討）

---

## 3. Superpowers ワークフロー（必須）

このプロジェクトの開発では、以下を必ず使用する：

- **機能追加・変更前**：`superpowers:brainstorming` で要件・設計を整理
- **複数ステップの実装前**：`superpowers:writing-plans` で実装計画を作成
- **実装時**：`superpowers:test-driven-development` に従い TDD で進める
- **完了前の検証**：`superpowers:verification-before-completion` で動作確認してから完了とする
- **コードレビュー受領時**：`superpowers:receiving-code-review` で指摘を精査してから実装

### ワークフローの例外（エスケープハッチ）

- UI の微細な調整（Streamlit ウィジェットのラベル変更・色調整など）やロジック変更を伴わない軽微な修正は、TDD や厳密な計画作成プロセスをスキップして即座に修正してよい
- `PROGRESS.md` が長くなりすぎた場合は、完了済みの古いタスクを自律的に削除・要約してスリム化すること（運用開始は Phase 1 以降。それまでは未使用でよい）

---

## 4. 進め方（このプロジェクトでの上書き）

- 仕様書の **Phase 1 → 7 の順** で進める。各 Phase の DoD は [仕様書 §10](docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md) を参照
- 待ち時間予測の精度限界（朝20分→昼60分の外れ）は **仕様であってバグではない**。当日2〜3回再生成する運用とセット。精度向上のための過剰実装は入れない
- 同行者は URL 共有による閲覧のみ。協調的編集機能は v1 では実装しない

---

## 5. 技術スタック（固定）

- Python 3.11+ / Streamlit / requests + BeautifulSoup / Pydantic / geopy / pandas / streamlit-local-storage
- DB は使わない（ローカル JSON で完結）
- デプロイは Streamlit Community Cloud
- **採用しなかった選択肢**：Next.js + Supabase（個人ツールに過剰）。蒸し返さない

### Streamlit Cloud の制約

- コンテナ再起動時にファイルシステムがリセットされる
- `data/snapshots/` の永続化は v1 では行わない（v2 以降で必要になったら別途検討）
- 無料枠は public repo のみ。private にしたいなら Streamlit Cloud 以外を検討

---

## 6. 来園日

**2026-05-25（月曜）**。営業時間・パレード時刻は 5/18 頃に公式サイトで確定する想定。
日程変更があった場合は、本ファイルと [仕様書 §16](docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md) の来園日固定情報を同時に更新する。
