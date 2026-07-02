# TDL Route Planner — 進捗ハンドオフ

**最終更新**: 2026-07-02（完了済み記録を [PROGRESS_archive_2026Q2.md](PROGRESS_archive_2026Q2.md) へ分離、冒頭ダイジェスト新設）

> 次セッションの Claude Code が状況を即時把握するための引き継ぎファイル。
> 実装の最終進捗は 2026-05-24（Phase 7 デプロイ完了）。来園日 2026-05-25 は終了済みで、現在は**休眠中**。

**🌐 本番 URL**: <https://park-route-planner-1-togo.streamlit.app>

---

## 📜 これまでの歩み（ダイジェスト）

- **第一命題**: 「リアルタイム待ち時間 × 最適ルート生成」。TDL 来園日（2026-05-25、家族 6 人 + 2 歳児 + ベビーカー）に使う個人ツール。公開・商用化なし
- **2026-05-16 始動**: TDS 向け旧構想を TDL 向けに全面ピボット。Python 3.11 + Streamlit + Pydantic、DB なしローカル JSON で確定（Next.js + Supabase は「個人ツールに過剰」で不採用）
- **Phase 1〜4（5/16〜19）**: scaffold / モデル / スクレイパー / マスタ / 距離・待ち時間予測。公式サイトが CSR と判明し HTML スクレイピング → 内部 JSON API 方式へ設計変更。座標 31 件は「Excel テンプレ + 検証付きインポーター」方式で東郷さんが入力（この 3 点セットは 5/24 の 14 件拡充でもそのまま再利用できた）
- **Phase 5〜6（5/20）**: 貪欲法ルーター（must-visit 優先 / DPA・食事・ショー固定ブロック / 雨天モード）+ Streamlit UI + localStorage 永続化
- **5/21**: シミュレーションモード新設（目的は「前日の心の準備・叩き台」。履歴データ蓄積案は ROI 過剰で不採用）。当日モードは「現在時刻・現在位置・乗った除外」のリアルタイム再生成に役割分担。Theme Park Warm デザイン適用 + UX 微改善 5 件、据置 7 件を確定
- **5/22（最大の転機）**: 「ライブ取得が動いている」は誤認で、実態は dummy snapshot への常時フォールバックと判明。原因は OLC 公式 API の WAF（curl/requests を TLS 指紋で黙殺）。撤退案を書きかけたが、東郷さんの「第一命題に向き合え」の指摘で第三者集約 API **Queue-Times.com（無料・5 分毎更新）へ切替**し完全解消。クレジット表示必須
- **5/23**: sim モード時刻軸拡張（任意時刻スタート + β 計算式補正、sim/live は「データソースだけ違う双子」に統合）。pass_type schema refactor（dpa_eligible → dpa/priority enum。2024 導入のプライオリティパス制度への追従漏れを東郷さん指摘で解消）。営業時間外 snapshot バグ + 二重消化バグ修正 → テスト 83 PASS
- **5/24（Phase 7 デプロイ完了）**: GitHub public repo（`hiroyuki-togo/park-route-planner-1`）+ Streamlit Community Cloud 稼働開始。クラウド UTC バグ（`datetime.now()` → `_now_jst()`）修正、休止 2 件削除 + 14 件マスタ拡充（20→34 件）
- **5/25 来園日（本番）**: 当日モードで実運用（実走結果の振り返り記録はセッションとして未作成）
- **現在地**: Phase 1〜7 全完了・本番稼働済み・休眠中。残りは K-* 小課題と v2 検討のみ

実装ログ・コミット単位の詳細・当時の意思決定記録の全文は [PROGRESS_archive_2026Q2.md](PROGRESS_archive_2026Q2.md) を参照。

---

## 1. 現在のステータス

**Phase 1〜7 全完了**。Streamlit Community Cloud でクラウド稼働中、家族・同行者共有可能。
**テスト 83/83 PASS**、マスタ **34 件** / レストラン 10 件。

### マスタ最終状態（34 件）

- **pass_type=dpa**: 3 件（beauty_and_beast / baymax / splash_mountain）
- **pass_type=priority**: 4 件（pooh / monsters_inc / haunted_mansion / star_tours）
- **Queue-Times ライブ取得対象**: 32 件
- **ライブ取得対象外（予測値運用）**: 2 件（**minnie_style** / **mickey_house** ← Queue-Times 未収録、既存の「⚠️ ライブ取得対象外」注記でカバー）

---

## 2. 未完了・保留タスク

### 既知の小課題（K-* シリーズ、再開時に拾う枠）

| ID | 内容 | 出典 |
|---|---|---|
| K-A | **latent risk**: `router.py` の `no_dpa_for_reserved` 警告は `requires_reservation=true` でトリガーされ、現状その対象は美女と野獣 / baymax の 2 件（どちらも `pass_type=dpa`）のみなので現時点で発火しない。ただし将来 `pass_type=priority` の行に `requires_reservation=true` を立てた場合、文言「DPA を登録してください」が pass_type 別になっていないため UX 不整合になる。文言を pass_type 別に振り分けるか、警告条件側に `pass_type` も組み込むか、別タスクで判断 | Final reviewer I-1 / Task 6 検討 |
| ~~K-B~~ | ~~内部 label `"DPA: {name}"`（app.py で DPA 入力済を表示する箇所）も pass_type 別に振り分けると UX 一貫性向上~~ → **5/23 夜に修正済**（コミット `f9c0520`、`label_prefix` で dpa/priority 振り分け） | Task 6 後の動作確認 |
| K-C | `Attraction` モデルに `model_config = ConfigDict(extra="forbid")` を入れると、今回の dpa_eligible silent-drop のような将来の fixture リファクタ事故を防げる（lessons #30） | Task 3 code reviewer M-3 |
| K-D | star_tours / splash_mountain の `avg_wait_min`（30 / 60 分）は 2026-05-23 時点の推測値。追加 14 件分も同様。実測値に置き換える余地 | Task 5 code reviewer M-3 |

### 据置決定（再議論禁止）

以下 7 件は 5/21 に判断済。**蒸し返すと CLAUDE.md §4「精度向上のための過剰実装は入れない」と整合性が崩れる**（検討経緯はアーカイブ §2「デザイン適用 + UX 微改善」参照）:

A1（スコア式）/ B2（並び順）/ B3（ルート表示の累計時間・地図）/ C1（予測精度）/ E1（カードに ✓ 消化済みボタン）/ E2（乗った一括クリア）/ E4（途中入園 sim 拡張）

### 補足

- 来園前の動作確認チェックリスト（一部未消化のまま）はアーカイブ §2 / §8 に残置。来園日終了に伴い実質クローズ
- v2 候補（TDS 対応 / TDR 共通化 / 地図プレビュー / snapshot 永続化 / DPA・スタンバイパス状況の活用）は着手前に `superpowers:brainstorming` から始めること

---

## 3. 確定した設計判断（コードから読み取れない判断）

- DPA 使用前提（コアアトラクションは DPA で乗る）
- 同行者は URL 共有による閲覧のみ（協調編集機能は v1 不実装）
- パレード：fixed_block 化、`watch=True` なら鑑賞・`False` ならメインストリート横断 +15 分ペナルティ
- 雨天モード：UI トグル、屋外 -30% 待ち時間 / 屋内 +20% / 移動係数 1.4→1.7 / 屋外 experience_value 0.7 倍
- 設定永続化：localStorage、日付スコープ（`tdl_settings_{YYYY-MM-DD}`）
- **ライブ取得は Queue-Times.com（park_id=274）経由**。OLC 公式 API は WAF が curl/requests を TLS 指紋で完全黙殺するため構造的に取得不可（lessons #23）。「Powered by Queue-Times.com」クレジット表示必須
- 営業時間外（9-21 外）のライブ snapshot は全件 closed になるため、内部的にシミュ計算（`build_snapshot_at()`）へ差し替える（lessons #31）
- クラウド（Streamlit Cloud）は UTC 固定。時刻は `_now_jst()` ヘルパー（`utcnow() + 9h`）で統一（lessons #33）

---

## 4. 環境メモ

- 作業ディレクトリ：`/Users/tougouhiroyuki/Projects/disney/`
- venv：`.venv/`（Python 3.11.15）
- pytest 実行：`.venv/bin/pytest -v`
- システム Python は 3.9.6（pyproject の `>=3.11` を満たさず、brew で 3.11 を別途インストール済み）
- GitHub アカウント：07jdp353@gmail.com（git config 設定済み、別プロジェクト [人事評価制度] と共存）
- GitHub repo：`hiroyuki-togo/park-route-planner-1`（public、5/24 push 済み）。Streamlit Cloud と webhook 連携済み
- Streamlit Cloud で反映されない時は「Manage app」→「Reboot app」（`@st.cache_data` キャッシュ一掃、lessons #34）

---

## 5. 関連ファイル

- [仕様書（正本）](docs/superpowers/specs/2026-05-16-tdl-route-planner-design.md)
- [実装計画](docs/superpowers/plans/2026-05-16-tdl-route-planner.md)
- [プロジェクト指示](CLAUDE.md)
- [意思決定経緯](memory.md)
- [教訓](lessons.md) ／ [教訓アーカイブ（全文）](lessons_archive.md)
- [進捗アーカイブ 2026Q2（完了済み実装ログ全文）](PROGRESS_archive_2026Q2.md)
- [TDS 向け旧仕様（参考）](archive/ディズニープラン-TDS.md)

---

## 6. 再開時の手引き

1. 冒頭の「📜 これまでの歩み」→ [CLAUDE.md](CLAUDE.md) → [lessons.md](lessons.md) の順で読む
2. `git status` クリーン確認 + `.venv/bin/pytest -q` で **83 passed** を確認
3. 本番 URL が生きているか確認（Streamlit Cloud 無料枠はアクセスが無いとスリープする。ダッシュボードから再起動可）
4. 着手候補: K-* 小課題（§2）または v2 検討（要ブレスト）。次の来園計画が決まったら、営業時間・パレード時刻・`requires_reservation` 対象・マスタ（休止/新設）の年次見直しから始める（lessons #25 / #28）
5. GitHub の用語（PR / branch / remote、UI の鉛筆アイコン等）は東郷さんが不慣れなので省略せず展開する（lessons #4）
