# pass_type スキーマ刷新 + マスタ整合性回復 — 設計仕様書

**作成日**: 2026-05-23
**ステータス**: ドラフト（東郷さんレビュー前）
**関連プラン**: 別途 `docs/superpowers/plans/2026-05-23-pass-type-schema-refactor.md` で作成予定
**前提**: Phase 7（デプロイ）着手前の必須修正として位置付ける

---

## 1. 背景

TDL は 2024 年に **プライオリティパス**（旧 FastPass 相当の無料優先入場制度）を導入した。これにより、現行 TDL の「優先入場手段」は **DPA（有料 1,500〜2,000 円）** と **プライオリティパス（無料）** の 2 系統となった。

しかし本プロジェクトの `data/attractions.json` および `src/models.py` は、プライオリティパス導入前（2023〜2024 前半）の状態で固まっており、**現実のマスタ整合性が崩れている**ことが 2026-05-23 セッションで判明した。Phase 7（デプロイ）で来園日 2026-05-25 に投入する前に整合性を回復する必要がある。

---

## 2. 現状の不整合（実証ベース）

東郷さん提供の公式情報（[公式 DPA ページ](https://www.tokyodisneyresort.jp/tdr/guide/app_service/disneypremieraccess.html) / [公式プライオリティパスページ](https://www.tokyodisneyresort.jp/en/tdr/guide/app_service/prioritypass.html)、2026-05-23 確認）と現マスタの比較:

| アトラクション | 公式現行 | 現マスタ | 状態 |
|---|---|---|---|
| 美女と野獣"魔法のものがたり" | DPA | `dpa_eligible: true, requires_reservation: true` | OK |
| ベイマックスのハッピーライド | DPA | `dpa_eligible: true` | OK |
| **スプラッシュ・マウンテン** | **DPA** | **マスタに無し** | ❌ 欠落 |
| プーさんのハニーハント | プライオリティ | `dpa_eligible: true` | ❌ 制度違い |
| モンスターズ・インク"ライド&ゴーシーク!" | プライオリティ | `dpa_eligible: true` | ❌ 制度違い |
| ビッグサンダー・マウンテン | プライオリティ | フラグなし | ❌ 未表現 |
| ホーンテッドマンション | プライオリティ | フラグなし | ❌ 未表現 |
| **スター・ツアーズ：ザ・アドベンチャーズ・コンティニュー** | **プライオリティ** | **マスタに無し** | ❌ 欠落 |

DPA ショー・パレード対象（昼パレード / 夜パレード / キャッスルプロジェクション、各 2,500 円）はデータモデル上のアトラクションではないため、本仕様の対象外（v1 では現状の `ShowBlock` / `ParadeBlock` の `watch=True` で代用、§5 参照）。

---

## 3. 設計

### 3.1 スキーマ変更

`src/models.py` の `Attraction` クラスから `dpa_eligible: bool` を削除し、`pass_type` を新設する。

```python
from typing import Literal, Optional

class Attraction(BaseModel):
    # ... 既存フィールド ...
    pass_type: Optional[Literal["dpa", "priority"]] = None
    # dpa_eligible は完全削除（後方互換シムを置かない、個人ツールのため）
```

**設計判断**:
- mutually exclusive な状態（DPA かつプライオリティ）を型で禁止するため、bool 2 個並列ではなく enum を採用
- 個人ツールのため `dpa_eligible` への後方互換シムは置かない（CLAUDE.md グローバル §「無駄な抽象化を入れない」）

### 3.2 マスタ修正（既存 6 件）

`data/attractions.json` の修正:

| ID | 変更内容 |
|---|---|
| `beauty_and_beast` | `dpa_eligible: true` 削除 → `pass_type: "dpa"`、`requires_reservation: true` は維持 |
| `pooh` | `dpa_eligible: true` 削除 → `pass_type: "priority"` |
| `monsters_inc` | `dpa_eligible: true` 削除 → `pass_type: "priority"` |
| `baymax` | `dpa_eligible: true` 削除 → `pass_type: "dpa"`、`requires_reservation: true` を新たに付与 |
| `big_thunder` | `pass_type: "priority"` 追加 |
| `haunted_mansion` | `pass_type: "priority"` 追加 |

他の 15 件は `pass_type` フィールド自体が無い状態（= `None`）で問題ない（Optional + default None のため）。明示的に `null` を書く必要も無い。

### 3.3 マスタ追加（新規 2 件）

| フィールド | star_tours | splash_mountain |
|---|---|---|
| `id` | `star_tours` | `splash_mountain` |
| `name` | スター・ツアーズ：ザ・アドベンチャーズ・コンティニュー | スプラッシュ・マウンテン |
| `scrape_key` | スター・ツアーズ | スプラッシュ |
| `area` | トゥモローランド | クリッターカントリー |
| `lat` | 35.63347071741284 | 35.63068751031142 |
| `lng` | 139.87831947363483 | 139.88318574387773 |
| `experience_time_min` | 7（実乗 5 分 + 前室解説 2 分） | 11（実乗 10 分 + ロード 1 分） |
| `queue_walk_min` | 3 | 3 |
| `default_priority` | 4 | 5 |
| `pass_type` | `priority` | `dpa` |
| `requires_reservation` | `false` | `false` |
| `outdoor` | `false`（シミュレーター屋内） | `false`（建物内、最後だけ屋外水しぶき） |
| `popularity_tier` | `A` | `S` |
| `queue_times_id` | Queue-Times.com から取得（取得不可なら `null`） | 同左 |
| `avg_wait_min` | Queue-Times.com の stats から（取得不可なら推測値 30 分） | 同左（推測値 60 分） |

`experience_time_min` と `popularity_tier` は東郷さんと既存アトラクションの値を参照して妥当な値を設定（star_tours は jungle_cruise / pirates 並み、splash_mountain は pooh / beauty_and_beast の中間想定）。

### 3.4 `requires_reservation` フラグの意味

このフラグは「DPA を取らないと実質乗れないレベル（待ち 200 分超え常態化）の絶望待ち時間」という意味で、ルーター側で `no_dpa_for_reserved` 警告のトリガーになっている。

**本仕様での扱い**:

| アトラクション | requires_reservation | 理由 |
|---|---|---|
| `beauty_and_beast` | `true`（現状維持） | TDL ナンバーワン待ち時間アトラクション |
| `baymax` | **`true` に変更** | 最新人気アトラクション、リニューアル控えで需要集中 |
| `splash_mountain` | `false`（新規追加） | DPA 対象だが「並べば乗れる」レベル想定 |
| プライオリティ系 5 件 | `false` | プライオリティパス対象（無料）なので構造的に DPA 必須にはならない |
| 上記以外 | `false` | フラグなし（現状維持） |

この結果、DPA 対象 3 件（beauty_and_beast / baymax / splash_mountain）のうち、`requires_reservation: true` は 2 件（美女と野獣 + ベイマックス）となる。

### 3.5 UI 変更（`app.py`）

最小限の 2 点のみ:

1. **expander ラベル**: 「DPA 入力」→「予約済み枠（DPA / プライオリティパス）」
2. **アトラクション選択肢のサフィックス**: `pass_type` が `dpa` なら `(DPA)`、`priority` なら `(プライオリティ)` を選択肢ラベル末尾に付与
   - 例: `美女と野獣"魔法のものがたり" (DPA)` / `ビッグサンダー・マウンテン (プライオリティ)`
   - `pass_type` が `None` のアトラクションは **「予約済み枠」入力 UI の選択肢から除外**（DPA / プライオリティ どちらも適用できないため）。通常のアトラクション設定 UI（priority slider + must-visit）には引き続き全件表示される。

UI 上、これ以外の変更は不要:
- 「⚠️ ライブ取得対象外」注記は `queue_times_id is None` を見ているので、新規 2 件で ID 取得失敗時も既存ロジックが自動対応
- `theme.py` のルートカードレンダラは `block_type` を見ているので影響なし
- ルート生成ロジック（router）も `pass_type` を直接見ない（fixed_blocks が時刻指定で挿入されるだけ）

### 3.6 scripts/import_attractions_from_xlsx.py の対応

Excel カラム名を `dpa_eligible` → `pass_type` に変更。Excel 側で空欄なら `None`、`"dpa"` / `"priority"` の文字列リテラル運用とする。Excel テンプレ生成スクリプト（`scripts/generate_attractions_template.py`）も同様に更新。

---

## 4. ショー/パレード DPA の扱い（v1 範囲外）

東郷さん提供情報では DPA は以下のショー/パレードも対象:
- ディズニー・ハーモニー・イン・カラー（昼のパレード）: 2,500 円
- 東京ディズニーランド・エレクトリカルパレード・ドリームライツ（夜のパレード）: 2,500 円
- キャッスルプロジェクション「Reach for the Stars」: 2,500 円

**v1 では新スキーマ追加せず、現状の `ShowBlock` / `ParadeBlock` の `watch=True` で代用する**。理由:
- ルーター視点では「その時刻はその場所にいる」だけ表現できれば十分（DPA 有料席かどうかは移動コストやペナルティに影響しない）
- 「DPA で買ったショー/パレード」と「指定席なしで観るショー/パレード」をデータモデルで区別する実益が v1 では薄い
- CLAUDE.md §4「精度向上のための過剰実装は入れない」と整合

v2 以降で「コスト追跡」「DPA バッジ表示」が必要になったら別途検討（YAGNI）。

---

## 5. テスト戦略

### 5.1 既存テスト 69 件の維持

- `tests/conftest.py` および各 `tests/test_*.py` の fixture 内の `dpa_eligible` 参照を全置換
- `pass_type` の正解値で fixture を書き換え、69 PASS を復活させる

### 5.2 新規追加テスト（TDD で書き起こす、Step 単位）

- **test_masters.py に追加**:
  - 全アトラクションの `pass_type` が `{"dpa", "priority", None}` のいずれか（型ガード）
  - star_tours / splash_mountain が存在し、座標が TDL 範囲内（既存ガード経由で自動）
  - pass_type=dpa のアトラクションが少なくとも 3 件存在（beauty_and_beast / baymax / splash_mountain）
  - pass_type=priority のアトラクションが少なくとも 5 件存在（big_thunder / pooh / haunted_mansion / star_tours / monsters_inc）
- **test_router.py に追加**:
  - pass_type=priority のアトラクションを must_visits に入れて DPA 入力なしの場合に `no_dpa_for_reserved` 警告が**出ない**こと（プライオリティパスは DPA 必須ではないため）

**目標テスト数**: 69 → 72 程度。

---

## 6. 実装順序（5 ステップ、各 step 後に動作確認）

| Step | 内容 | テスト状態 | コミット粒度 |
|---|---|---|---|
| 1 | `src/models.py` で `pass_type` 追加 + `dpa_eligible` 削除 | 一旦壊れる | 1 commit |
| 2 | `data/attractions.json` 既存 6 件を `pass_type` に書き換え + scripts/import_attractions_from_xlsx.py / scripts/generate_attractions_template.py 対応 | 一旦壊れる | 1 commit |
| 3 | テスト fixture と router/scraper の `dpa_eligible` 参照を `pass_type` に全置換 | **69 PASS 復活** | 1 commit |
| 4 | star_tours と splash_mountain をマスタ追加（Queue-Times 経由で queue_times_id / avg_wait_min 自動取得）+ test_masters.py に新規ガード追加 | 71-72 PASS | 1 commit |
| 5 | UI（app.py の expander ラベルと選択肢サフィックス）変更 + Streamlit 目視確認 | 71-72 PASS | 1 commit |

Step 3 終了時点で「コード整合性は回復、データ整合性は道半ば」、Step 4 で「データ整合性も完了」となる。

---

## 7. 非対象（YAGNI / 据置）

以下は本仕様の対象外:

- **ショー/パレード DPA のデータモデル化**（§4 で説明、v1 範囲外）
- **DPA / プライオリティパスのコスト表示**（東郷さんが運用で把握、UI 表示不要）
- **プライオリティパスのクールダウン管理**（取得戦略はユーザー判断）
- **dpa_eligible への後方互換シム**（個人ツールのため不要）
- **マスタ全体の年次見直し**（lessons #25 に記録済の運用課題で、本仕様の scope ではない）

---

## 8. 影響範囲（実装着手前に grep で再確認）

`dpa_eligible` を参照する可能性のあるファイル（要 Step 1 前 grep）:

- `src/models.py` — 定義
- `data/attractions.json` — 値
- `src/router.py` — ロジック内参照（要確認）
- `src/scraper.py` — Queue-Times パース時の参照（要確認）
- `app.py` — UI 選択肢生成時の参照（要確認）
- `scripts/import_attractions_from_xlsx.py` / `scripts/generate_attractions_template.py` — I/O
- `tests/conftest.py` / `tests/test_*.py` — fixture

Step 1 着手前に `grep -rn dpa_eligible` で漏れなく洗い出す。

---

## 9. 完了基準（DoD）

- [ ] `src/models.py` の `Attraction` に `pass_type` 追加、`dpa_eligible` 削除済
- [ ] `data/attractions.json` の既存 6 件を `pass_type` に書き換え済、新規 2 件追加済
- [ ] `pytest -q` で 71 件以上 PASS
- [ ] Streamlit 起動して当日モード / sim モード両方でアトラクション選択肢に pass_type サフィックスが出る
- [ ] DPA 入力 expander のラベルが「予約済み枠（DPA / プライオリティパス）」になっている
- [ ] スター・ツアーズ / スプラッシュマウンテンが選択肢に出る（座標 / queue_times_id / avg_wait_min が確定済 or null フォールバック動作確認済）
- [ ] PROGRESS.md / lessons.md 更新（lessons は「マスタ整合性は年次見直しで」「pass_type enum 設計判断の経緯」など）

---

## 10. 参考リンク

- [TDL 公式 DPA ページ](https://www.tokyodisneyresort.jp/tdr/guide/app_service/disneypremieraccess.html)
- [TDL 公式プライオリティパスページ](https://www.tokyodisneyresort.jp/en/tdr/guide/app_service/prioritypass.html)
- [Queue-Times.com TDL](https://queue-times.com/parks/274/queue_times.json)
- [CLAUDE.md](../../../CLAUDE.md)
- [PROGRESS.md](../../../PROGRESS.md)
- [lessons.md](../../../lessons.md)
