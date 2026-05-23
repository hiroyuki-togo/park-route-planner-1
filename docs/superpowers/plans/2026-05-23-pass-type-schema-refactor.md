# pass_type Schema Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `dpa_eligible: bool` with `pass_type: "dpa" | "priority" | None` enum, correct 6 existing attractions' pass flags, add 2 missing attractions (Star Tours, Splash Mountain), and reflect the changes in the Streamlit UI — before Phase 7 deployment.

**Architecture:** Pydantic model first (single source of truth), then data file migration, then test fixtures, then UI. TDD throughout; each task ends with `pytest -q` passing and a focused commit.

**Tech Stack:** Python 3.11 / Pydantic v2 / pytest / Streamlit / requests (for Queue-Times.com lookup).

**Spec:** [docs/superpowers/specs/2026-05-23-pass-type-schema-refactor-design.md](../specs/2026-05-23-pass-type-schema-refactor-design.md)

---

## File Structure

**Modify:**
- `src/models.py` — `Attraction` フィールド変更
- `data/attractions.json` — 既存 6 件の修正 + 新規 2 件追加
- `scripts/generate_attractions_template.py` — Excel テンプレ列の更新
- `app.py` — UI 選択肢生成ロジック + expander ラベル
- `tests/conftest.py` / `tests/test_models.py` / `tests/test_router.py` / `tests/test_predictor.py` — fixture の `dpa_eligible` 全置換
- `PROGRESS.md` / `lessons.md` — ハンドオフ更新と学びの記録

**Create:**
- `scripts/lookup_queue_times_ids.py` — Queue-Times.com から ID と avg_wait_min を抽出する 1 回限りのスクリプト（star_tours / splash_mountain 用）

**Not touching:**
- `scripts/import_coordinates_from_xlsx.py` — 座標専用、pass_type は対象外
- `src/router.py` / `src/scraper.py` — grep 結果に dpa_eligible なし（影響なし）
- `theme.py` — block_type ベース、pass_type の影響なし

---

## Task 1: src/models.py の pass_type 移行

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 失敗テストを書く（pass_type 受け入れ）**

`tests/test_models.py` に以下のテストを追加（既存テストの直下に挿入）:

```python
def test_attraction_pass_type_dpa():
    attr = Attraction(
        id="test_dpa",
        name="Test DPA",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        pass_type="dpa",
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type == "dpa"


def test_attraction_pass_type_priority():
    attr = Attraction(
        id="test_priority",
        name="Test Priority",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        pass_type="priority",
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type == "priority"


def test_attraction_pass_type_default_none():
    attr = Attraction(
        id="test_none",
        name="Test None",
        scrape_key="Test",
        area="Test Area",
        lat=35.63,
        lng=139.88,
        experience_time_min=5,
        queue_walk_min=2,
        default_priority=3,
        outdoor=False,
        popularity_tier="A",
    )
    assert attr.pass_type is None


def test_attraction_pass_type_invalid_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Attraction(
            id="test_invalid",
            name="Test Invalid",
            scrape_key="Test",
            area="Test Area",
            lat=35.63,
            lng=139.88,
            experience_time_min=5,
            queue_walk_min=2,
            default_priority=3,
            pass_type="freepass",  # invalid enum value
            outdoor=False,
            popularity_tier="A",
        )
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `.venv/bin/pytest tests/test_models.py::test_attraction_pass_type_dpa -v`

Expected: FAIL with `ValidationError: extra inputs not permitted (pass_type)` または類似のエラー（現状 dpa_eligible しかないため）。

- [ ] **Step 3: src/models.py を修正**

`src/models.py` の `Attraction` クラス内で:

1. `from typing import Literal, Optional` が import 行にない場合は追加
2. `dpa_eligible: bool = False` の行を削除
3. 同じ位置に追加:

```python
    pass_type: Optional[Literal["dpa", "priority"]] = None
```

- [ ] **Step 4: 新規 4 テストが PASS することを確認**

Run: `.venv/bin/pytest tests/test_models.py -v`

Expected: 新規 4 テスト PASS。既存テストは fixture が dpa_eligible 参照のためエラーする可能性あり（次のタスクで解消）。

- [ ] **Step 5: コミット**

```bash
git add src/models.py tests/test_models.py
git commit -m "$(cat <<'EOF'
refactor(models): replace dpa_eligible with pass_type enum

Attraction.dpa_eligible: bool → pass_type: Optional[Literal["dpa", "priority"]]。
無料プライオリティパス制度（2024 導入）と DPA を mutually exclusive な
enum で表現。後方互換シムは置かない（個人ツールのため）。

EOF
)"
```

---

## Task 2: data/attractions.json 既存 6 件の修正

**Files:**
- Modify: `data/attractions.json`

- [ ] **Step 1: 修正方針を確認**

修正対象 6 件 + 内容:

| ID | dpa_eligible 削除 | pass_type 追加 | requires_reservation |
|---|---|---|---|
| `beauty_and_beast` | はい | `"dpa"` | true 維持 |
| `baymax` | はい | `"dpa"` | **false → true に変更** |
| `pooh` | はい | `"priority"` | (なし) |
| `monsters_inc` | はい | `"priority"` | (なし) |
| `big_thunder` | (元から無し) | `"priority"` 新規 | (なし) |
| `haunted_mansion` | (元から無し) | `"priority"` 新規 | (なし) |

他の 13 件は `dpa_eligible` を持っていれば削除（`false` を持っていた場合は単純削除、`true` を持っていた場合は本タスクの対象に含まれているはずなので想定外）。

- [ ] **Step 2: data/attractions.json を手で編集**

Edit ツールで以下を実行:

**beauty_and_beast** (`dpa_eligible: true` の行を削除し、`requires_reservation: true` の上に `pass_type: "dpa"` を挿入):

```
"dpa_eligible": true,
```
↓ 削除し、代わりに同じ位置に:
```
"pass_type": "dpa",
```

**baymax**: `dpa_eligible: true` を `pass_type: "dpa"` に置換 + `requires_reservation: false` を `requires_reservation: true` に変更。

**pooh / monsters_inc**: `dpa_eligible: true` を `pass_type: "priority"` に置換。

**big_thunder / haunted_mansion**: `requires_reservation: false` の行の直後に `"pass_type": "priority",` を挿入。

その他 13 件で `dpa_eligible: false` の行があれば削除（grep で確認）。

- [ ] **Step 3: テストで整合性確認**

Run: `.venv/bin/pytest tests/test_masters.py -v`

Expected: PASS（既存テストはマスタの構造的妥当性のみ検証しているため、pass_type 追加で壊れない想定）。fixture を介さず attractions.json を直接読むので、Task 3 を待たずに通る。

NG なら attractions.json の JSON 構文エラーなのでチェック。

- [ ] **Step 4: コミット**

```bash
git add data/attractions.json
git commit -m "$(cat <<'EOF'
data: migrate 6 attractions to pass_type and fix制度違い

- beauty_and_beast / baymax: dpa
- pooh / monsters_inc: priority (現実は無料制度。旧マスタの誤分類を訂正)
- big_thunder / haunted_mansion: priority (現実は無料制度、未表現だった)
- baymax: requires_reservation を true に昇格（リニューアル控えで需要集中）

EOF
)"
```

---

## Task 3: テスト fixture の dpa_eligible 全置換

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_router.py`
- Modify: `tests/test_predictor.py`
- Modify: `tests/test_models.py`
- Modify: `app.py`
- Modify: `scripts/generate_attractions_template.py`

- [ ] **Step 1: dpa_eligible 参照箇所を全件確認**

Run:
```bash
grep -rn "dpa_eligible" --include="*.py" --include="*.json"
```

Expected: 上記 6 ファイルが該当（data/attractions.json は Task 2 で既に処理済）。

- [ ] **Step 2: tests/conftest.py の fixture を変換**

`dpa_eligible=True` を `pass_type="dpa"` に、`dpa_eligible=False` は行ごと削除。Edit ツールで該当行を 1 件ずつ修正。

- [ ] **Step 3: tests/test_router.py / tests/test_predictor.py / tests/test_models.py の同様置換**

各ファイルで `dpa_eligible=True` → `pass_type="dpa"`、`dpa_eligible=False` → 行削除。Edit ツールで個別対応。

- [ ] **Step 4: app.py の dpa_eligible 参照を pass_type に置換**

app.py 内で `a.dpa_eligible` のような参照を `a.pass_type is not None` または対応する文脈の式に置換（例: 「予約済み枠」入力時のフィルタは「dpa or priority のいずれかが付いているもの」になるため `attr.pass_type is not None` が正しい）。

Read で app.py の該当箇所を確認した上で、文脈に合わせて Edit。

- [ ] **Step 5: scripts/generate_attractions_template.py の更新**

Excel テンプレ生成スクリプトの `dpa_eligible` 列を `pass_type` に変更。デフォルト値は空文字列。コメント / docstring も同期更新。

- [ ] **Step 6: 全テスト実行で 69 PASS 復活確認**

Run: `.venv/bin/pytest -q`

Expected: 69 + Task 1 で追加した 4 = **73 passed**。

NG が出たら個別に修正。

- [ ] **Step 7: コミット**

```bash
git add tests/ app.py scripts/generate_attractions_template.py
git commit -m "$(cat <<'EOF'
refactor: migrate all dpa_eligible references to pass_type

fixture / app.py / Excel テンプレ生成スクリプトの dpa_eligible 参照を
pass_type に全置換。テスト 73 件 PASS 復活。

EOF
)"
```

---

## Task 4: Queue-Times.com から star_tours / splash_mountain の ID と avg_wait_min を取得

**Files:**
- Create: `scripts/lookup_queue_times_ids.py`

- [ ] **Step 1: 1 回限りの lookup スクリプトを作成**

`scripts/lookup_queue_times_ids.py` を新規作成:

```python
"""Queue-Times.com から star_tours / splash_mountain の ID と avg_wait_min を抽出する 1 回限りのスクリプト。

実行後、出力をコピペして data/attractions.json に手動で反映する。
"""
from __future__ import annotations

import json

import requests

QUEUE_TIMES_URL = "https://queue-times.com/parks/274/queue_times.json"
TARGETS = {
    "star_tours": ["Star Tours", "スター・ツアーズ", "Star tours"],
    "splash_mountain": ["Splash Mountain", "スプラッシュ"],
}


def fetch_attractions() -> list[dict]:
    resp = requests.get(QUEUE_TIMES_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    out: list[dict] = []
    for land in data.get("lands", []):
        for ride in land.get("rides", []):
            out.append(ride)
    return out


def main() -> None:
    rides = fetch_attractions()
    print(f"Queue-Times から {len(rides)} 件取得\n")
    for our_id, candidates in TARGETS.items():
        match = None
        for ride in rides:
            name = ride.get("name", "")
            for cand in candidates:
                if cand.lower() in name.lower():
                    match = ride
                    break
            if match:
                break
        if match:
            print(f"✓ {our_id}:")
            print(f"  queue_times_id = {match['id']}")
            print(f"  name (QT) = {match['name']}")
            print(f"  current wait = {match.get('wait_time', 'N/A')} 分")
            print(f"  is_open = {match.get('is_open')}")
        else:
            print(f"✗ {our_id}: 該当なし")
        print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: スクリプトを実行**

Run: `.venv/bin/python scripts/lookup_queue_times_ids.py`

Expected: 標準出力に star_tours と splash_mountain の `queue_times_id` が表示される。

該当なしの場合、Queue-Times の name フィールド規則を確認し、TARGETS の候補リストを調整して再実行。

avg_wait_min は Queue-Times の `/queue_times` JSON には含まれないため、別途 `https://queue-times.com/parks/274/rides/<id>/stats` をブラウザで確認するか、avg なしで運用する。**取れない場合は推測値**（star_tours=30 分 / splash_mountain=60 分）を採用する。

- [ ] **Step 3: コミット**

```bash
git add scripts/lookup_queue_times_ids.py
git commit -m "$(cat <<'EOF'
chore: add one-off Queue-Times ID lookup script

star_tours / splash_mountain の queue_times_id を抽出する 1 回限りの
スクリプト。実行結果を attractions.json に手動反映する運用。

EOF
)"
```

---

## Task 5: star_tours と splash_mountain をマスタに追加

**Files:**
- Modify: `data/attractions.json`
- Test: `tests/test_masters.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/test_masters.py` に追加:

```python
def test_star_tours_and_splash_mountain_exist(attractions_data):
    ids = {a["id"] for a in attractions_data["attractions"]}
    assert "star_tours" in ids, "スター・ツアーズが attractions.json に無い"
    assert "splash_mountain" in ids, "スプラッシュマウンテンが attractions.json に無い"


def test_pass_type_values_are_valid(attractions_data):
    for a in attractions_data["attractions"]:
        pass_type = a.get("pass_type")
        assert pass_type in (None, "dpa", "priority"), (
            f"{a['id']} の pass_type が不正: {pass_type}"
        )


def test_dpa_attractions_count(attractions_data):
    dpa = [a for a in attractions_data["attractions"] if a.get("pass_type") == "dpa"]
    assert len(dpa) == 3, f"DPA 対象は 3 件のはずだが {len(dpa)} 件"
    dpa_ids = {a["id"] for a in dpa}
    assert dpa_ids == {"beauty_and_beast", "baymax", "splash_mountain"}


def test_priority_pass_attractions_count(attractions_data):
    pri = [a for a in attractions_data["attractions"] if a.get("pass_type") == "priority"]
    assert len(pri) == 5, f"プライオリティ対象は 5 件のはずだが {len(pri)} 件"
    pri_ids = {a["id"] for a in pri}
    assert pri_ids == {
        "big_thunder",
        "pooh",
        "haunted_mansion",
        "star_tours",
        "monsters_inc",
    }
```

`attractions_data` fixture が test_masters.py に既にあるはず（前提）。無い場合は conftest.py を確認。

- [ ] **Step 2: テストが失敗することを確認**

Run: `.venv/bin/pytest tests/test_masters.py::test_star_tours_and_splash_mountain_exist -v`

Expected: FAIL with "スター・ツアーズが attractions.json に無い"。

- [ ] **Step 3: data/attractions.json に 2 件追加**

attractions 配列の末尾（`omnibus` の後）に以下の 2 件を追加。`queue_times_id` と `avg_wait_min` は Task 4 の結果で確定した値を使う。取れなかった場合は `null` / 推測値（30 or 60）。

```json
    {
      "id": "star_tours",
      "name": "スター・ツアーズ：ザ・アドベンチャーズ・コンティニュー",
      "scrape_key": "スター・ツアーズ",
      "area": "トゥモローランド",
      "lat": 35.63347071741284,
      "lng": 139.87831947363483,
      "experience_time_min": 7,
      "queue_walk_min": 3,
      "default_priority": 4,
      "pass_type": "priority",
      "requires_reservation": false,
      "outdoor": false,
      "popularity_tier": "A",
      "queue_times_id": <Task 4 結果 or null>,
      "avg_wait_min": <Task 4 結果 or 30>
    },
    {
      "id": "splash_mountain",
      "name": "スプラッシュ・マウンテン",
      "scrape_key": "スプラッシュ",
      "area": "クリッターカントリー",
      "lat": 35.63068751031142,
      "lng": 139.88318574387773,
      "experience_time_min": 11,
      "queue_walk_min": 3,
      "default_priority": 5,
      "pass_type": "dpa",
      "requires_reservation": false,
      "outdoor": false,
      "popularity_tier": "S",
      "queue_times_id": <Task 4 結果 or null>,
      "avg_wait_min": <Task 4 結果 or 60>
    }
```

- [ ] **Step 4: テスト PASS を確認**

Run: `.venv/bin/pytest tests/test_masters.py -v`

Expected: 新規 4 テスト含めて全 PASS。

`.venv/bin/pytest -q` で全体も確認。Task 3 末尾の 73 → 77 になる想定。

- [ ] **Step 5: コミット**

```bash
git add data/attractions.json tests/test_masters.py
git commit -m "$(cat <<'EOF'
data: add star_tours and splash_mountain to attractions master

仕様書 §3.3 に従い欠落していた 2 件を追加。両方ともプライオリティ /
DPA 対応で、待ち時間予測 / ルート生成 / ライブ取得対象に組み込まれる。

EOF
)"
```

---

## Task 6: app.py の UI ラベルと選択肢サフィックス

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 該当箇所を Read で確認**

`app.py` 内の「DPA 入力」expander の現在の実装を確認:

```bash
grep -n "DPA" app.py | head -20
```

該当箇所の文脈（expander のラベル / 選択肢 selectbox / アトラクションフィルタ）を Read で把握。

- [ ] **Step 2: expander ラベル変更**

Edit で:
```
with st.expander("DPA 入力", ...):
```
↓
```
with st.expander("予約済み枠（DPA / プライオリティパス）入力", ...):
```

正確な文言は現状の expander 行の状況に合わせる（既存ラベル末尾の `expanded=False` などはそのまま）。

- [ ] **Step 3: アトラクション選択肢に pass_type サフィックスを付与**

DPA 入力の selectbox / multiselect で使われている選択肢生成ロジックを修正:

```python
def _pass_type_label(attr):
    if attr.pass_type == "dpa":
        return " (DPA)"
    if attr.pass_type == "priority":
        return " (プライオリティ)"
    return ""

dpa_candidates = [a for a in attractions if a.pass_type is not None]
dpa_options = {f"{a.name}{_pass_type_label(a)}": a.id for a in dpa_candidates}
```

正確な実装は既存の selectbox / multiselect の引数構造に合わせて整える。

- [ ] **Step 4: Streamlit を立ち上げて目視確認**

Run: `.venv/bin/streamlit run app.py` （別ターミナル想定 or background run）

ブラウザで `localhost:8501` を開き:
- 「予約済み枠（DPA / プライオリティパス）」expander のラベルが正しい
- 選択肢に `美女と野獣"魔法のものがたり" (DPA)` / `ビッグサンダー・マウンテン (プライオリティ)` のように pass_type が出ている
- pass_type=None のアトラクション（pirates / jungle_cruise 等）は選択肢に出てこない
- アトラクション設定セクション（priority slider）には全件が変わらず出ている

- [ ] **Step 5: テストで全体 PASS 確認**

Run: `.venv/bin/pytest -q`

Expected: 77 passed（Task 5 末尾と同じ）。

- [ ] **Step 6: コミット**

```bash
git add app.py
git commit -m "$(cat <<'EOF'
feat(ui): label DPA/Priority pass options with type suffix

- expander ラベルを「予約済み枠（DPA / プライオリティパス）」に変更
- 選択肢に (DPA) / (プライオリティ) サフィックス
- pass_type=None のアトラクションは予約枠選択肢から除外

EOF
)"
```

---

## Task 7: ドキュメント更新（PROGRESS.md / lessons.md）

**Files:**
- Modify: `PROGRESS.md`
- Modify: `lessons.md`

- [ ] **Step 1: PROGRESS.md の更新**

`PROGRESS.md` を Read。以下の更新を入れる:

1. ヘッダー部の最終更新日を `2026-05-23` に保持（既に同日）し、追記:
   > pass_type スキーマ刷新 + マスタ整合性回復完了（テスト 77 件 PASS）
2. §1 現在のステータスの「5/23 セッション」末尾に Phase 7 着手前の本タスク完了を 1 段落追加
3. §2 完了済みタスクに「pass_type schema refactor」のサブセクションを追加（コミット 7 件の表）
4. §3 次にやることを **Phase 7 のみ** に絞り、pass_type 関連項目を除去

- [ ] **Step 2: lessons.md に新規学びを追加**

以下の 2 件を追記（既存末尾に追加）:

**#28**: マスタデータの年次見直しを怠ると、データソース API が変わる前から内部矛盾でルートが歪む
（pooh / monsters_inc が DPA フラグのままだった件、プライオリティパス制度導入から 1 年以上気付かなかった件の振り返り）

**#29**: 後方互換シムは個人ツールでは負債になる
（dpa_eligible → pass_type の移行で、後方互換を置かず一気に切り替えた判断と、その判断軸）

- [ ] **Step 3: コミット**

```bash
git add PROGRESS.md lessons.md
git commit -m "$(cat <<'EOF'
docs: update PROGRESS/lessons for pass_type refactor completion

77 テスト PASS、マスタ整合性回復済。Phase 7（デプロイ）着手前条件が整った。

EOF
)"
```

---

## 完了条件

- [ ] `.venv/bin/pytest -q` で 77 passed
- [ ] Streamlit 起動で UI 確認済（expander ラベル / 選択肢サフィックス）
- [ ] `git log --oneline -10` で本プランの 7 コミットが見える
- [ ] `git status` クリーン
- [ ] PROGRESS.md / lessons.md 更新済
- [ ] 次セッションは Phase 7（デプロイ）に進める状態

---

## 関連

- **Spec**: [docs/superpowers/specs/2026-05-23-pass-type-schema-refactor-design.md](../specs/2026-05-23-pass-type-schema-refactor-design.md)
- **次プラン**: [docs/superpowers/plans/2026-05-23-phase-7-deployment.md](2026-05-23-phase-7-deployment.md)
- **CLAUDE.md**: [../../CLAUDE.md](../../../CLAUDE.md)
- **PROGRESS.md**: [../../PROGRESS.md](../../../PROGRESS.md)
