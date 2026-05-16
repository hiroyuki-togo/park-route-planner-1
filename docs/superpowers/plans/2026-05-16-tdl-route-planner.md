# TDL Route Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 東京ディズニーランド（TDL）来園日（2026-05-25）に使う、リアルタイム待ち時間取得 + 終日ルート自動生成の個人ツールを構築する。

**Architecture:** Streamlit 単体アプリ + ローカル JSON マスタ。`src/` 配下に責務別モジュール（scraper / predictor / distance / router / models / constants）、`app.py` で UI、`data/` でマスタとスナップショット。仕様書（[design doc](../specs/2026-05-16-tdl-route-planner-design.md)）の Phase 1〜7 を順次実装。

**Tech Stack:** Python 3.11+ / Streamlit / requests + BeautifulSoup / Pydantic / geopy / pandas / streamlit-local-storage / pytest

---

## ファイル構成

実装で作成するファイル：

| ファイル | 責務 |
|---|---|
| `pyproject.toml` | 依存パッケージとプロジェクト設定 |
| `.gitignore` | Python 標準 + `data/snapshots/` |
| `.env.example` | 環境変数雛形（v1 では実質空） |
| `README.md` | 概要・起動方法・デプロイ手順 |
| `requirements.txt` | Streamlit Cloud 用（pyproject.toml から生成） |
| `app.py` | Streamlit UI 全体 |
| `src/__init__.py` | 空 |
| `src/constants.py` | TIME_FACTOR / POPULARITY_FACTOR / AREAS / MAIN_STREET_BLOCKING_PAIRS / 開園・閉園時間 |
| `src/models.py` | Pydantic モデル：Attraction / Restaurant / FixedBlock / DpaReservation / RouteStep / RouteResult / WaitTimeSnapshot / Warning |
| `src/scraper.py` | 公式サイトから待ち時間取得、ファジーマッチ、5分キャッシュ、フォールバック |
| `src/predictor.py` | 時間帯×人気度×天候による待ち時間予測 |
| `src/distance.py` | geopy + park_factor + パレード横断ペナルティ + 雨天補正 |
| `src/router.py` | 貪欲法ルート生成、must-visit、DPA、固定ブロック衝突回避、警告生成 |
| `data/attractions.json` | アトラクションマスタ（Phase 3 で雛形生成 → 人力で座標埋め） |
| `data/restaurants.json` | レストランマスタ（Phase 3 で雛形生成 → 人力で座標埋め） |
| `tests/__init__.py` | 空 |
| `tests/test_scraper.py` | fixture HTML ベースの抽出テスト |
| `tests/test_predictor.py` | 予測式の境界条件テスト |
| `tests/test_distance.py` | 距離・パレード・雨天補正テスト |
| `tests/test_router.py` | ルート生成ロジックの分岐網羅テスト |
| `tests/fixtures/sample_realtime.html` | 公式サイトを保存した HTML |
| `tests/conftest.py` | 共通フィクスチャ（サンプルマスタ、スナップショット） |

---

## Phase 1：プロジェクト初期化

### Task 1: リポジトリ初期化と pyproject.toml 作成

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: git init し、最初のコミット用意**

Run: `cd /Users/tougouhiroyuki/Projects/disney && git init && git status`
Expected: 既存ファイル（CLAUDE.md, memory.md, docs/, archive/）が untracked として表示される

- [ ] **Step 2: `pyproject.toml` を作成**

```toml
[project]
name = "tdl-route-planner"
version = "0.1.0"
description = "Personal route planner for Tokyo Disneyland"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.36",
    "requests>=2.32",
    "beautifulsoup4>=4.12",
    "pydantic>=2.7",
    "geopy>=2.4",
    "pandas>=2.2",
    "streamlit-local-storage>=0.0.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 3: `.gitignore` を作成**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/

# Project
data/snapshots/
.env

# OS
.DS_Store
```

- [ ] **Step 4: `.env.example` を作成（v1 では空運用）**

```
# v1 では機密情報なし。Streamlit Cloud デプロイ時も追加不要。
```

- [ ] **Step 5: ディレクトリ構造を作成**

Run:
```bash
mkdir -p src tests/fixtures data/snapshots
touch src/__init__.py tests/__init__.py
```
Expected: ディレクトリが作成され、空の `__init__.py` が2つ生成される

- [ ] **Step 6: コミット**

```bash
git add pyproject.toml .gitignore .env.example src/__init__.py tests/__init__.py
git commit -m "chore: bootstrap project scaffold and Python packaging"
```

---

### Task 2: 仮想環境と依存インストール

**Files:** なし（環境構築のみ）

- [ ] **Step 1: 仮想環境作成（uv 優先、なければ venv）**

Run:
```bash
which uv && uv venv .venv || python3.11 -m venv .venv
```
Expected: `.venv/` が作成される

- [ ] **Step 2: 依存インストール**

Run（uv の場合）:
```bash
source .venv/bin/activate
uv pip install -e ".[dev]"
```

または（venv + pip の場合）:
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: streamlit, pydantic, pytest 等がインストールされる

- [ ] **Step 3: 動作確認**

Run: `python -c "import streamlit, pydantic, pytest; print('OK')"`
Expected: `OK`

---

### Task 3: 定数モジュール `src/constants.py`

**Files:**
- Create: `src/constants.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_constants.py
from src.constants import (
    TIME_FACTOR, POPULARITY_FACTOR, AREAS,
    OPEN_TIME, CLOSE_TIME,
    PARK_FACTOR_NORMAL, PARK_FACTOR_RAIN,
    WALKING_SPEED_M_PER_MIN,
    MAIN_STREET_BLOCKING_PAIRS,
    get_time_factor,
)


def test_time_factor_peak():
    assert get_time_factor(12) == 1.3


def test_time_factor_morning():
    assert get_time_factor(9) == 0.7


def test_time_factor_evening():
    assert get_time_factor(20) == 0.7


def test_popularity_factor_keys():
    assert set(POPULARITY_FACTOR.keys()) == {"S", "A", "B", "C"}


def test_areas_seven():
    assert len(AREAS) == 7
    assert "ワールドバザール" in AREAS


def test_main_street_pairs_is_frozenset():
    for pair in MAIN_STREET_BLOCKING_PAIRS:
        assert isinstance(pair, frozenset)
        assert len(pair) == 2
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_constants.py -v`
Expected: ImportError で全部失敗

- [ ] **Step 3: `src/constants.py` を実装**

```python
"""TDL Route Planner の定数定義。"""

OPEN_TIME = "09:00"
CLOSE_TIME = "21:00"

WALKING_SPEED_M_PER_MIN = 67  # 4 km/h
PARK_FACTOR_NORMAL = 1.4
PARK_FACTOR_RAIN = 1.7

AREAS = [
    "ワールドバザール",
    "アドベンチャーランド",
    "ウエスタンランド",
    "クリッターカントリー",
    "ファンタジーランド",
    "トゥーンタウン",
    "トゥモローランド",
]

# 時間帯補正係数：時刻（hour）→ 待ち時間係数
TIME_FACTOR = {
    (9, 10): 0.7,
    (10, 11): 0.9,
    (11, 14): 1.3,
    (14, 17): 1.2,
    (17, 19): 1.0,
    (19, 21): 0.7,
}

POPULARITY_FACTOR = {"S": 1.0, "A": 0.9, "B": 0.8, "C": 0.7}

EXP_VALUE = {"S": 10, "A": 7, "B": 5, "C": 3}

DPA_WAIT_MIN = 15

# パレード時間中、メインストリートを横断する移動に +15 分ペナルティ
MAIN_STREET_PENALTY_MIN = 15

# Phase 4 で実地経験 + Google マップを見ながら具体ペアを確定する
MAIN_STREET_BLOCKING_PAIRS = {
    frozenset(["トゥモローランド", "アドベンチャーランド"]),
    frozenset(["トゥモローランド", "ウエスタンランド"]),
    frozenset(["ファンタジーランド", "アドベンチャーランド"]),
}


def get_time_factor(hour: int) -> float:
    """指定した時刻に対応する待ち時間係数を返す。"""
    for (start, end), factor in TIME_FACTOR.items():
        if start <= hour < end:
            return factor
    return 1.0
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_constants.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/constants.py tests/test_constants.py
git commit -m "feat: add constants module with time factors, areas, and parade pairs"
```

---

### Task 4: Pydantic モデル `src/models.py`

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_models.py
from datetime import datetime, time

from src.models import (
    Attraction, Restaurant, FixedBlock, DpaReservation,
    RouteStep, RouteResult, WaitTimeSnapshot, WaitTimeEntry, Warning,
)


def test_attraction_valid():
    a = Attraction(
        id="pooh", name="プーさんのハニーハント", scrape_key="プーさん",
        area="ファンタジーランド", lat=35.63, lng=139.88,
        experience_time_min=5, queue_walk_min=3,
        default_priority=4, dpa_eligible=True,
        requires_reservation=False, outdoor=False,
        popularity_tier="S",
    )
    assert a.id == "pooh"


def test_attraction_tier_validation():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Attraction(
            id="x", name="x", scrape_key="x", area="x",
            lat=0, lng=0, experience_time_min=1, queue_walk_min=1,
            default_priority=1, dpa_eligible=False,
            requires_reservation=False, outdoor=False,
            popularity_tier="X",  # invalid
        )


def test_fixed_block_dpa_needs_attraction_id():
    block = FixedBlock(
        type="dpa",
        start=datetime(2026, 5, 25, 10, 30),
        end=datetime(2026, 5, 25, 11, 30),
        label="DPA: 美女と野獣",
        attraction_id="beauty_and_beast",
        location=(35.63, 139.88),
    )
    assert block.attraction_id == "beauty_and_beast"


def test_dpa_reservation():
    r = DpaReservation(
        attraction_id="beauty_and_beast",
        start=time(10, 30), end=time(11, 30),
    )
    assert r.start.hour == 10


def test_route_result_empty():
    r = RouteResult(steps=[], unvisited_musts=[], warnings=[])
    assert r.steps == []
```

```python
# tests/test_models.py の先頭に追加
import pytest
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_models.py -v`
Expected: ImportError

- [ ] **Step 3: `src/models.py` を実装**

```python
"""Pydantic モデル定義。"""
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field


PopularityTier = Literal["S", "A", "B", "C"]
RestaurantType = Literal["table_service", "buffet", "counter_service"]
BlockType = Literal["meal", "show", "parade", "dpa"]
StepType = Literal["attraction", "meal", "show", "parade", "dpa"]
StatusType = Literal["operating", "closed", "unknown"]
WeatherMode = Literal["normal", "rain"]


class Attraction(BaseModel):
    id: str
    name: str
    scrape_key: str
    area: str
    lat: float
    lng: float
    experience_time_min: int = Field(ge=0)
    queue_walk_min: int = Field(ge=0, default=0)
    default_priority: int = Field(ge=1, le=5)
    dpa_eligible: bool = False
    requires_reservation: bool = False
    outdoor: bool = False
    popularity_tier: PopularityTier


class Restaurant(BaseModel):
    id: str
    name: str
    area: str
    lat: float
    lng: float
    type: RestaurantType
    ps_available: bool = False
    typical_duration_min: int = Field(ge=1)
    open_window: tuple[str, str]  # ("11:00", "21:30")


class FixedBlock(BaseModel):
    type: BlockType
    start: datetime
    end: datetime
    label: str
    attraction_id: str | None = None
    restaurant_id: str | None = None
    location: tuple[float, float] | None = None
    watch: bool = False


class DpaReservation(BaseModel):
    attraction_id: str
    start: time
    end: time


class WaitTimeEntry(BaseModel):
    name: str
    wait_min: int | None
    status: StatusType


class WaitTimeSnapshot(BaseModel):
    timestamp: datetime
    park: str
    data: list[WaitTimeEntry]


class RouteStep(BaseModel):
    type: StepType
    id: str | None
    arrive: datetime
    ride_start: datetime
    ride_end: datetime
    travel_min: float
    wait_min: float
    via: Literal["standby", "dpa"] | None = None
    label: str | None = None


class Warning(BaseModel):
    kind: Literal["time_conflict", "dpa_window_missed", "no_dpa_for_reserved"]
    message: str
    attraction_id: str | None = None


class RouteResult(BaseModel):
    steps: list[RouteStep]
    unvisited_musts: list[str]
    warnings: list[Warning]
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_models.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add Pydantic models for attractions, blocks, routes, warnings"
```

---

## Phase 2：データ取得実装（JSON API ベース）

**設計変更メモ（2026-05-16）**：当初 HTML スクレイピング想定だったが、実際の TDL サイトはクライアントサイドレンダリングで、データは内部 JSON API（`/_/realtime/tdl_attraction.json`）から取得される。HTML 直接取得ではデータが入らないため、JSON API ベースに切り替え。仕様書 §4 参照。

### Task 5: 公式 JSON API のサンプルレスポンスを fixture として保存（完了済み）

**Files:**
- Create: `tests/fixtures/sample_realtime.json`（JSON データ、47KB）
- Create: `tests/fixtures/sample_realtime.html`（HTML 構造の参考、1.8MB）

Status：**完了**（commit `5dd970e`）。公式 JSON API から実データを取得・保存済み。

Fixture の構造：JSON は配列で、各要素が 1 アトラクション。主要フィールドは `FacilityName`、`StandbyTime`、`OperatingStatusCD`、`OperatingStatus`、`UpdateTime`、`DPAStatusCD`、`FsStatusCD`。

---

### Task 6: スクレイパー — JSON 抽出

**Files:**
- Create: `src/scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_scraper.py
from pathlib import Path

from src.scraper import parse_json_to_entries


FIXTURE = Path(__file__).parent / "fixtures" / "sample_realtime.json"


def test_parse_returns_entries():
    raw = FIXTURE.read_text(encoding="utf-8")
    entries = parse_json_to_entries(raw)
    assert len(entries) > 5
    for e in entries:
        assert e.name
        assert e.status in ("operating", "closed", "unknown")


def test_parse_status_closed_when_operating_status_cd_002():
    """OperatingStatusCD == "002" は closed に分類される。"""
    raw = '[{"FacilityName": "テスト", "StandbyTime": null, "OperatingStatusCD": "002", "OperatingStatus": "案内終了"}]'
    entries = parse_json_to_entries(raw)
    assert len(entries) == 1
    assert entries[0].status == "closed"
    assert entries[0].wait_min is None


def test_parse_status_operating_when_standby_time_present():
    raw = '[{"FacilityName": "テスト", "StandbyTime": 30, "OperatingStatusCD": "001", "OperatingStatus": "運営中"}]'
    entries = parse_json_to_entries(raw)
    assert entries[0].status == "operating"
    assert entries[0].wait_min == 30


def test_parse_status_unknown_when_no_data():
    """StandbyTime null かつ OperatingStatusCD が 002 以外は unknown。"""
    raw = '[{"FacilityName": "テスト", "StandbyTime": null, "OperatingStatusCD": "003", "OperatingStatus": "運営状況確認中"}]'
    entries = parse_json_to_entries(raw)
    assert entries[0].status == "unknown"
    assert entries[0].wait_min is None
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `.venv/bin/pytest tests/test_scraper.py -v`
Expected: ImportError

- [ ] **Step 3: `src/scraper.py` の最小実装**

```python
"""TDL 公式 JSON API から待ち時間データを取得・パースする。"""
from __future__ import annotations

import json

from src.models import WaitTimeEntry


def parse_json_to_entries(raw: str | list) -> list[WaitTimeEntry]:
    """JSON 文字列 or 配列からアトラクションエントリのリストを抽出する。"""
    data = json.loads(raw) if isinstance(raw, str) else raw
    entries: list[WaitTimeEntry] = []
    for item in data:
        name = (item.get("FacilityName") or "").strip()
        if not name:
            continue
        standby = item.get("StandbyTime")
        op_cd = item.get("OperatingStatusCD")
        wait_min, status = _classify(standby, op_cd)
        entries.append(WaitTimeEntry(name=name, wait_min=wait_min, status=status))
    return entries


def _classify(standby: int | None, op_cd: str | None) -> tuple[int | None, str]:
    """StandbyTime と OperatingStatusCD から (wait_min, status) を判定する。"""
    if op_cd == "002":
        return None, "closed"
    if standby is None:
        return None, "unknown"
    return int(standby), "operating"
```

- [ ] **Step 4: テスト再実行**

Run: `.venv/bin/pytest tests/test_scraper.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/scraper.py tests/test_scraper.py
git commit -m "feat: parse TDL realtime JSON into wait time entries"
```

---

### Task 7: スクレイパー — ファジーマッチで scrape_key 解決

**Files:**
- Modify: `src/scraper.py`
- Modify: `tests/test_scraper.py`

- [ ] **Step 1: テスト追加**

```python
# tests/test_scraper.py に追加
from src.scraper import match_attraction_by_scrape_key


def test_fuzzy_match_exact():
    entries = [
        WaitTimeEntry(name="プーさんのハニーハント", wait_min=30, status="operating"),
        WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=45, status="operating"),
    ]
    result = match_attraction_by_scrape_key(entries, "プーさん")
    assert result.name == "プーさんのハニーハント"


def test_fuzzy_match_none():
    entries = [
        WaitTimeEntry(name="プーさん", wait_min=30, status="operating"),
    ]
    result = match_attraction_by_scrape_key(entries, "存在しないアトラクション")
    assert result is None
```

ファイル先頭の import に `from src.models import WaitTimeEntry` を追加。

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_scraper.py::test_fuzzy_match_exact tests/test_scraper.py::test_fuzzy_match_none -v`
Expected: ImportError

- [ ] **Step 3: `src/scraper.py` に追加**

```python
# src/scraper.py に追加
from difflib import SequenceMatcher


def match_attraction_by_scrape_key(
    entries: list[WaitTimeEntry], scrape_key: str, threshold: float = 0.6
) -> WaitTimeEntry | None:
    """scrape_key とエントリ名をファジーマッチして最も近いものを返す。"""
    best: WaitTimeEntry | None = None
    best_score = 0.0
    for e in entries:
        score = SequenceMatcher(None, scrape_key, e.name).ratio()
        # 部分一致もボーナス
        if scrape_key in e.name:
            score += 0.3
        if score > best_score:
            best_score = score
            best = e
    return best if best_score >= threshold else None
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_scraper.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/scraper.py tests/test_scraper.py
git commit -m "feat: fuzzy match scrape_key against snapshot entries"
```

---

### Task 8: スクレイパー — ネットワーク取得 + キャッシュ + フォールバック

**Files:**
- Modify: `src/scraper.py`
- Modify: `tests/test_scraper.py`

- [ ] **Step 1: テスト追加（モックベース）**

```python
# tests/test_scraper.py に追加
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.scraper import fetch_realtime_wait_times, _is_cache_fresh


def test_cache_fresh_within_5min():
    last = datetime.now() - timedelta(minutes=3)
    assert _is_cache_fresh(last) is True


def test_cache_fresh_after_5min():
    last = datetime.now() - timedelta(minutes=6)
    assert _is_cache_fresh(last) is False


def test_fetch_uses_fallback_on_error(tmp_path):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    sample = {
        "timestamp": "2026-05-25T09:00:00",
        "park": "TDL",
        "data": [{"name": "プーさん", "wait_min": 30, "status": "operating"}],
    }
    (snap_dir / "2026-05-25_0900.json").write_text(json.dumps(sample))

    with patch("src.scraper.requests.get", side_effect=Exception("network error")):
        snapshot = fetch_realtime_wait_times(snapshot_dir=snap_dir, force=True)

    assert snapshot is not None
    assert snapshot.park == "TDL"
    assert len(snapshot.data) == 1
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `.venv/bin/pytest tests/test_scraper.py -v`
Expected: ImportError on new symbols

- [ ] **Step 3: `src/scraper.py` に追加**

```python
# src/scraper.py に追加
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.models import WaitTimeSnapshot


TDL_JSON_URL = "https://www.tokyodisneyresort.jp/_/realtime/tdl_attraction.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CACHE_TTL_MIN = 5
REQUEST_TIMEOUT_SEC = 30


def _is_cache_fresh(last_fetch: datetime | None) -> bool:
    if last_fetch is None:
        return False
    return (datetime.now() - last_fetch) < timedelta(minutes=CACHE_TTL_MIN)


def _latest_snapshot_file(snapshot_dir: Path) -> Path | None:
    files = sorted(snapshot_dir.glob("*.json"))
    return files[-1] if files else None


def _load_snapshot_from_file(path: Path) -> WaitTimeSnapshot:
    raw = json.loads(path.read_text())
    return WaitTimeSnapshot.model_validate(raw)


def fetch_realtime_wait_times(
    snapshot_dir: Path = Path("data/snapshots"),
    force: bool = False,
) -> WaitTimeSnapshot | None:
    """公式 JSON API から取得し、失敗時は直近スナップショットにフォールバック。"""
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            TDL_JSON_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        entries = parse_json_to_entries(resp.text)
        snapshot = WaitTimeSnapshot(
            timestamp=datetime.now(),
            park="TDL",
            data=entries,
        )
        ts = snapshot.timestamp.strftime("%Y-%m-%d_%H%M")
        (snapshot_dir / f"{ts}.json").write_text(snapshot.model_dump_json())
        return snapshot

    except Exception:
        latest = _latest_snapshot_file(snapshot_dir)
        if latest:
            return _load_snapshot_from_file(latest)
        return None
```

- [ ] **Step 4: テスト再実行**

Run: `.venv/bin/pytest tests/test_scraper.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/scraper.py tests/test_scraper.py
git commit -m "feat: fetch JSON with retry/fallback and 5min cache check"
```

---

## Phase 3：マスタ整備（半人力）

### Task 9: アトラクションマスタ雛形生成スクリプト

**Files:**
- Create: `scripts/generate_attractions_template.py`
- Create: `data/attractions.json`

- [ ] **Step 1: 雛形生成スクリプトを作成**

```python
# scripts/generate_attractions_template.py
"""TDL アトラクションマスタの雛形を生成する。
lat/lng は null で出力、後で人力で埋める。"""
import json
from pathlib import Path


ATTRACTIONS = [
    # ファンタジーランド
    ("beauty_and_beast", "美女と野獣\"魔法のものがたり\"", "美女と野獣", "ファンタジーランド", 7, "S", True, True, False),
    ("pooh", "プーさんのハニーハント", "プーさん", "ファンタジーランド", 5, "S", True, False, False),
    ("peter_pan", "ピーターパン空の旅", "ピーターパン", "ファンタジーランド", 3, "A", False, False, False),
    ("haunted_mansion", "ホーンテッドマンション", "ホーンテッドマンション", "ファンタジーランド", 10, "A", False, False, False),
    ("its_a_small_world", "イッツ・ア・スモールワールド", "スモールワールド", "ファンタジーランド", 10, "B", False, False, False),
    ("snow_white", "白雪姫と七人のこびと", "白雪姫", "ファンタジーランド", 2, "A", False, False, False),
    # トゥモローランド
    ("monsters_inc", "モンスターズ・インク \"ライド&ゴーシーク!\"", "モンスターズ・インク", "トゥモローランド", 4, "S", True, False, False),
    ("buzz", "バズ・ライトイヤーのアストロブラスター", "バズ", "トゥモローランド", 4, "A", False, False, False),
    ("baymax", "ベイマックスのハッピーライド", "ベイマックス", "トゥモローランド", 2, "S", True, False, True),
    # トゥーンタウン
    ("minnie_style", "ミニーのスタイルスタジオ", "ミニーのスタイル", "トゥーンタウン", 5, "B", False, False, False),
    ("roger_rabbit", "ロジャーラビットのカートゥーンスピン", "ロジャーラビット", "トゥーンタウン", 4, "B", False, False, False),
    # ウエスタンランド
    ("big_thunder", "ビッグサンダー・マウンテン", "ビッグサンダー", "ウエスタンランド", 4, "A", False, False, True),
    ("mark_twain", "蒸気船マークトウェイン号", "マークトウェイン", "ウエスタンランド", 12, "C", False, False, True),
    ("country_bear", "カントリーベア・シアター", "カントリーベア", "ウエスタンランド", 15, "C", False, False, False),
    # クリッターカントリー（スプラッシュ閉鎖後の現存アトラクションのみ）
    ("beaver_brothers", "ビーバーブラザーズのカヌー探険", "ビーバーブラザーズ", "クリッターカントリー", 12, "C", False, False, True),
    # アドベンチャーランド
    ("jungle_cruise", "ジャングルクルーズ", "ジャングルクルーズ", "アドベンチャーランド", 10, "B", False, False, True),
    ("pirates", "カリブの海賊", "カリブの海賊", "アドベンチャーランド", 15, "A", False, False, False),
    ("western_river", "ウエスタンリバー鉄道", "ウエスタンリバー", "アドベンチャーランド", 15, "C", False, False, True),
    ("swiss_family", "スイスファミリー・ツリーハウス", "ツリーハウス", "アドベンチャーランド", 10, "C", False, False, True),
    ("enchanted_tiki", "魅惑のチキルーム", "チキルーム", "アドベンチャーランド", 10, "C", False, False, False),
    # ワールドバザール（アトラクションは少なめ）
    ("omnibus", "オムニバス", "オムニバス", "ワールドバザール", 5, "C", False, False, True),
]


def main():
    data = {
        "park": "TDL",
        "open_time": "09:00",
        "close_time": "21:00",
        "entrance": {"lat": 35.6329, "lng": 139.8804},
        "attractions": [
            {
                "id": id_,
                "name": name,
                "scrape_key": key,
                "area": area,
                "lat": None,
                "lng": None,
                "experience_time_min": exp,
                "queue_walk_min": 3,
                "default_priority": 5 if tier == "S" else (4 if tier == "A" else 3),
                "dpa_eligible": dpa,
                "requires_reservation": reserve,
                "outdoor": outdoor,
                "popularity_tier": tier,
            }
            for id_, name, key, area, exp, tier, dpa, reserve, outdoor in ATTRACTIONS
        ],
    }
    out = Path("data/attractions.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Wrote {len(data['attractions'])} attractions to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: スクリプトを実行**

Run: `python scripts/generate_attractions_template.py`
Expected: `Wrote 21 attractions to data/attractions.json`

- [ ] **Step 3: 生成された JSON を目視確認**

Run: `head -30 data/attractions.json`
Expected: `park`, `entrance`, `attractions` が含まれ、各アトラクションの `lat`/`lng` が `null`

- [ ] **Step 4: コミット**

```bash
git add scripts/generate_attractions_template.py data/attractions.json
git commit -m "data: generate TDL attractions master template with null coords"
```

- [ ] **Step 5: 人力タスクのメモ**

東郷さんへ：このタスク完了後、以下を手作業で実施：

1. Google マップで各アトラクション入口を検索
2. 右クリック → 座標コピーで lat/lng を取得
3. `data/attractions.json` の `null` を実数値で置換
4. 美女と野獣の `requires_reservation` が現状の運用で正しいか公式サイトで確認

完了後の作業確認テストは Task 11 で書く。

---

### Task 10: レストランマスタ雛形生成

**Files:**
- Create: `scripts/generate_restaurants_template.py`
- Create: `data/restaurants.json`

- [ ] **Step 1: スクリプトを作成**

```python
# scripts/generate_restaurants_template.py
"""TDL 主要レストランマスタの雛形を生成する。"""
import json
from pathlib import Path


# (id, name, area, type, ps_available, typical_duration_min, open_start, open_end)
RESTAURANTS = [
    # テーブルサービス（PS 対応）
    ("blue_bayou", "ブルーバイユー・レストラン", "アドベンチャーランド", "table_service", True, 90, "11:00", "21:30"),
    ("crystal_palace", "クリスタルパレス・レストラン", "ワールドバザール", "buffet", True, 75, "11:00", "21:30"),
    ("eastside_cafe", "イーストサイド・カフェ", "ワールドバザール", "table_service", True, 75, "11:00", "21:30"),
    ("hokusai", "れすとらん北齋", "ワールドバザール", "table_service", True, 75, "11:00", "21:30"),
    ("diamond_horseshoe", "ザ・ダイヤモンドホースシュー", "ウエスタンランド", "buffet", True, 75, "11:30", "20:30"),
    # カウンターサービス（PS なし、待ちは目安）
    ("pan_galactic", "パン・ギャラクティック・ピザ・ポート", "トゥモローランド", "counter_service", False, 35, "10:30", "21:00"),
    ("plazma_rays", "プラズマ・レイズ・ダイナー", "トゥモローランド", "counter_service", False, 35, "10:30", "21:00"),
    ("hungry_bear", "ハングリーベア・レストラン", "ウエスタンランド", "counter_service", False, 35, "10:30", "21:00"),
    ("queen_of_hearts", "クイーン・オブ・ハートのバンケットホール", "ファンタジーランド", "counter_service", False, 35, "10:30", "21:00"),
    ("huey_dewey_louie", "ヒューイ・デューイ・ルーイのグッドタイム・カフェ", "トゥーンタウン", "counter_service", False, 35, "10:30", "21:00"),
]


def main():
    data = {
        "park": "TDL",
        "restaurants": [
            {
                "id": id_,
                "name": name,
                "area": area,
                "lat": None,
                "lng": None,
                "type": type_,
                "ps_available": ps,
                "typical_duration_min": dur,
                "open_window": [start, end],
            }
            for id_, name, area, type_, ps, dur, start, end in RESTAURANTS
        ],
    }
    out = Path("data/restaurants.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Wrote {len(data['restaurants'])} restaurants to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: スクリプト実行**

Run: `python scripts/generate_restaurants_template.py`
Expected: `Wrote 10 restaurants to data/restaurants.json`

- [ ] **Step 3: コミット**

```bash
git add scripts/generate_restaurants_template.py data/restaurants.json
git commit -m "data: generate TDL restaurants master template (10 stores)"
```

- [ ] **Step 4: 人力タスクのメモ**

東郷さんへ：各レストラン入口の座標を Google マップで取得し、`null` を埋める。

---

### Task 11: マスタ妥当性検証テスト

**Files:**
- Create: `tests/test_masters.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_masters.py
"""data/attractions.json と data/restaurants.json の妥当性を検証する。"""
import json
from pathlib import Path

from src.constants import AREAS
from src.models import Attraction, Restaurant


def test_attractions_all_loadable():
    raw = json.loads(Path("data/attractions.json").read_text())
    for a in raw["attractions"]:
        # lat/lng が埋まっていればモデル化できる
        if a["lat"] is not None and a["lng"] is not None:
            Attraction.model_validate(a)


def test_attractions_areas_valid():
    raw = json.loads(Path("data/attractions.json").read_text())
    for a in raw["attractions"]:
        assert a["area"] in AREAS, f"unknown area: {a['area']} for {a['id']}"


def test_attractions_unique_ids():
    raw = json.loads(Path("data/attractions.json").read_text())
    ids = [a["id"] for a in raw["attractions"]]
    assert len(ids) == len(set(ids)), "duplicate attraction ids"


def test_attractions_coordinates_filled():
    """全アトラクションの lat/lng が埋まっていることを確認（マスタ整備完了の DoD）。"""
    raw = json.loads(Path("data/attractions.json").read_text())
    unfilled = [a["id"] for a in raw["attractions"] if a["lat"] is None or a["lng"] is None]
    assert unfilled == [], f"coordinates missing for: {unfilled}"


def test_restaurants_all_loadable():
    raw = json.loads(Path("data/restaurants.json").read_text())
    for r in raw["restaurants"]:
        if r["lat"] is not None and r["lng"] is not None:
            Restaurant.model_validate(r)


def test_restaurants_coordinates_filled():
    raw = json.loads(Path("data/restaurants.json").read_text())
    unfilled = [r["id"] for r in raw["restaurants"] if r["lat"] is None or r["lng"] is None]
    assert unfilled == [], f"coordinates missing for: {unfilled}"
```

- [ ] **Step 2: テスト実行**

Run: `pytest tests/test_masters.py -v`
Expected: `test_attractions_coordinates_filled` と `test_restaurants_coordinates_filled` は **人力タスク完了まで FAIL**（これが DoD）。他のテストは PASS。

- [ ] **Step 3: コミット**

```bash
git add tests/test_masters.py
git commit -m "test: validate attractions/restaurants master integrity"
```

人力タスク完了の確認：`pytest tests/test_masters.py -v` が全 PASS になったら Phase 3 完了。

---

## Phase 4：距離・予測

### Task 12: 距離計算 — 基本 + 雨天モード

**Files:**
- Create: `src/distance.py`
- Create: `tests/test_distance.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_distance.py
from datetime import datetime

from src.distance import travel_time_min
from src.models import FixedBlock


# 同エリア内（プーさん→ホーンテッドマンション、目安50m）
LOC_A = (35.6330, 139.8810)
LOC_B = (35.6333, 139.8815)
# 城を跨ぐ移動（トゥモローランド→アドベンチャーランド）
LOC_TOMORROW = (35.6320, 139.8830)
LOC_ADVENTURE = (35.6315, 139.8790)


def test_short_distance_normal():
    t = travel_time_min(LOC_A, LOC_B, current_time=datetime(2026, 5, 25, 12, 0), fixed_blocks=[])
    assert 0 < t < 5


def test_rain_increases_time():
    base = travel_time_min(LOC_A, LOC_B, datetime(2026, 5, 25, 12, 0), [], weather_mode="normal")
    rain = travel_time_min(LOC_A, LOC_B, datetime(2026, 5, 25, 12, 0), [], weather_mode="rain")
    assert rain > base


def test_parade_penalty_applies():
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=False,
    )
    # トゥモロー → アドベンチャー は MAIN_STREET_BLOCKING_PAIRS に含まれる
    base = travel_time_min(LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [])
    with_parade = travel_time_min(LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade])
    assert with_parade >= base + 15


def test_parade_watch_no_penalty():
    """watch=True のパレードは鑑賞中であり、横断ペナルティは無関係。"""
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=True,
    )
    base = travel_time_min(LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [])
    with_parade = travel_time_min(LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade])
    assert with_parade == base
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_distance.py -v`
Expected: ImportError

- [ ] **Step 3: `src/distance.py` を実装**

```python
"""距離・移動時間の計算。"""
from __future__ import annotations

from datetime import datetime

from geopy.distance import geodesic

from src.constants import (
    AREAS, MAIN_STREET_BLOCKING_PAIRS, MAIN_STREET_PENALTY_MIN,
    PARK_FACTOR_NORMAL, PARK_FACTOR_RAIN, WALKING_SPEED_M_PER_MIN,
)
from src.models import FixedBlock


def travel_time_min(
    loc_a: tuple[float, float],
    loc_b: tuple[float, float],
    current_time: datetime,
    fixed_blocks: list[FixedBlock],
    weather_mode: str = "normal",
    area_a: str | None = None,
    area_b: str | None = None,
) -> float:
    """二点間の移動時間（分）を返す。"""
    distance_m = geodesic(loc_a, loc_b).meters
    park_factor = PARK_FACTOR_RAIN if weather_mode == "rain" else PARK_FACTOR_NORMAL
    base = distance_m / WALKING_SPEED_M_PER_MIN * park_factor

    if area_a and area_b and _crosses_main_street(area_a, area_b):
        for block in fixed_blocks:
            if block.type == "parade" and not block.watch:
                if block.start <= current_time <= block.end:
                    base += MAIN_STREET_PENALTY_MIN
                    break

    return base


def _crosses_main_street(area_a: str, area_b: str) -> bool:
    return frozenset([area_a, area_b]) in MAIN_STREET_BLOCKING_PAIRS
```

- [ ] **Step 4: テスト実行**

Run: `pytest tests/test_distance.py -v`
Expected: `test_short_distance_normal` と `test_rain_increases_time` は PASS。`test_parade_penalty_applies` 系は **area 引数なしでは false** になるため失敗。

- [ ] **Step 5: テストを `area_a` / `area_b` 付きに修正**

```python
# tests/test_distance.py の test_parade_penalty_applies と test_parade_watch_no_penalty を修正

def test_parade_penalty_applies():
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=False,
    )
    base = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    with_parade = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    assert with_parade >= base + 15


def test_parade_watch_no_penalty():
    parade = FixedBlock(
        type="parade",
        start=datetime(2026, 5, 25, 13, 30),
        end=datetime(2026, 5, 25, 14, 15),
        label="Harmony in Color",
        watch=True,
    )
    base = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    with_parade = travel_time_min(
        LOC_TOMORROW, LOC_ADVENTURE, datetime(2026, 5, 25, 13, 45), [parade],
        area_a="トゥモローランド", area_b="アドベンチャーランド",
    )
    assert with_parade == base
```

- [ ] **Step 6: テスト再実行**

Run: `pytest tests/test_distance.py -v`
Expected: 全 PASS

- [ ] **Step 7: コミット**

```bash
git add src/distance.py tests/test_distance.py
git commit -m "feat: travel time with park factor, weather mode, parade penalty"
```

---

### Task 13: 待ち時間予測

**Files:**
- Create: `src/predictor.py`
- Create: `tests/test_predictor.py`

- [ ] **Step 1: テスト作成**

```python
# tests/test_predictor.py
from datetime import datetime, timedelta

from src.models import Attraction
from src.predictor import predict_wait


def make_attraction(tier="S", outdoor=False):
    return Attraction(
        id="x", name="X", scrape_key="X", area="ファンタジーランド",
        lat=35.63, lng=139.88, experience_time_min=5, queue_walk_min=3,
        default_priority=5, dpa_eligible=False,
        requires_reservation=False, outdoor=outdoor,
        popularity_tier=tier,
    )


def test_within_30min_returns_current():
    now = datetime(2026, 5, 25, 10, 0)
    target = now + timedelta(minutes=20)
    assert predict_wait(make_attraction(), 30, now, target) == 30


def test_peak_hour_increases_wait():
    """9時(0.7)→12時(1.3) の遷移で wait が増える。"""
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    predicted = predict_wait(make_attraction("S"), 30, now, target)
    assert predicted > 30


def test_evening_decreases_wait():
    """12時(1.3)→20時(0.7) の遷移で wait が減る。"""
    now = datetime(2026, 5, 25, 12, 0)
    target = datetime(2026, 5, 25, 20, 0)
    predicted = predict_wait(make_attraction("S"), 60, now, target)
    assert predicted < 60


def test_tier_s_swings_more_than_c():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    pred_s = predict_wait(make_attraction("S"), 30, now, target)
    pred_c = predict_wait(make_attraction("C"), 30, now, target)
    assert pred_s > pred_c


def test_minimum_wait_clamped_to_5():
    now = datetime(2026, 5, 25, 12, 0)
    target = datetime(2026, 5, 25, 20, 0)
    predicted = predict_wait(make_attraction("S"), 5, now, target)
    assert predicted >= 5


def test_rain_decreases_outdoor():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    outdoor = make_attraction("S", outdoor=True)
    normal = predict_wait(outdoor, 30, now, target, weather_mode="normal")
    rain = predict_wait(outdoor, 30, now, target, weather_mode="rain")
    assert rain < normal


def test_rain_increases_indoor():
    now = datetime(2026, 5, 25, 9, 30)
    target = datetime(2026, 5, 25, 12, 30)
    indoor = make_attraction("S", outdoor=False)
    normal = predict_wait(indoor, 30, now, target, weather_mode="normal")
    rain = predict_wait(indoor, 30, now, target, weather_mode="rain")
    assert rain > normal
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_predictor.py -v`
Expected: ImportError

- [ ] **Step 3: `src/predictor.py` を実装**

```python
"""待ち時間予測。"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.constants import POPULARITY_FACTOR, get_time_factor
from src.models import Attraction


def predict_wait(
    attraction: Attraction,
    current_wait: int,
    current_time: datetime,
    target_time: datetime,
    weather_mode: str = "normal",
) -> float:
    """target_time 時点の待ち時間を予測する。"""
    if target_time - current_time < timedelta(minutes=30):
        return float(current_wait)

    factor_now = get_time_factor(current_time.hour)
    factor_then = get_time_factor(target_time.hour)
    pop_factor = POPULARITY_FACTOR[attraction.popularity_tier]

    delta = (factor_then - factor_now) * pop_factor
    predicted = current_wait * (1 + delta)

    if weather_mode == "rain":
        predicted *= 0.7 if attraction.outdoor else 1.2

    return max(5.0, predicted)
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_predictor.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/predictor.py tests/test_predictor.py
git commit -m "feat: wait time prediction with time/popularity/weather factors"
```

---

## Phase 5：ルート生成

### Task 14: ルーター — 共通フィクスチャと最小ケース

**Files:**
- Create: `tests/conftest.py`
- Create: `src/router.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: `tests/conftest.py` を作成**

```python
# tests/conftest.py
from datetime import datetime

import pytest

from src.models import Attraction, WaitTimeEntry, WaitTimeSnapshot


@pytest.fixture
def sample_attractions():
    return [
        Attraction(
            id="pooh", name="プーさんのハニーハント", scrape_key="プーさん",
            area="ファンタジーランド", lat=35.6330, lng=139.8810,
            experience_time_min=5, queue_walk_min=3, default_priority=5,
            dpa_eligible=True, requires_reservation=False, outdoor=False,
            popularity_tier="S",
        ),
        Attraction(
            id="big_thunder", name="ビッグサンダー・マウンテン", scrape_key="ビッグサンダー",
            area="ウエスタンランド", lat=35.6322, lng=139.8780,
            experience_time_min=4, queue_walk_min=3, default_priority=4,
            dpa_eligible=False, requires_reservation=False, outdoor=True,
            popularity_tier="A",
        ),
        Attraction(
            id="beauty_and_beast", name="美女と野獣", scrape_key="美女と野獣",
            area="ファンタジーランド", lat=35.6336, lng=139.8808,
            experience_time_min=7, queue_walk_min=5, default_priority=5,
            dpa_eligible=True, requires_reservation=True, outdoor=False,
            popularity_tier="S",
        ),
    ]


@pytest.fixture
def operating_snapshot():
    return WaitTimeSnapshot(
        timestamp=datetime(2026, 5, 25, 9, 0),
        park="TDL",
        data=[
            WaitTimeEntry(name="プーさんのハニーハント", wait_min=30, status="operating"),
            WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=20, status="operating"),
            WaitTimeEntry(name="美女と野獣", wait_min=120, status="operating"),
        ],
    )


@pytest.fixture
def all_closed_snapshot():
    return WaitTimeSnapshot(
        timestamp=datetime(2026, 5, 25, 9, 0),
        park="TDL",
        data=[
            WaitTimeEntry(name="プーさんのハニーハント", wait_min=None, status="closed"),
            WaitTimeEntry(name="ビッグサンダー・マウンテン", wait_min=None, status="closed"),
            WaitTimeEntry(name="美女と野獣", wait_min=None, status="closed"),
        ],
    )
```

- [ ] **Step 2: 最小テスト作成**

```python
# tests/test_router.py
from datetime import datetime

from src.models import FixedBlock
from src.router import RouteConstraints, generate_route


def make_constraints():
    return RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[],
    )


def test_all_closed_returns_empty(sample_attractions, all_closed_snapshot):
    result = generate_route(
        snapshot=all_closed_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    assert result.steps == []


def test_basic_route_visits_high_priority(sample_attractions, operating_snapshot):
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 4, "beauty_and_beast": 5},
        must_visits=set(),
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    # 美女と野獣は requires_reservation=True で DPA なしなので除外される
    assert "beauty_and_beast" not in visited_ids
    # 残り2件が訪問される
    assert "pooh" in visited_ids
    assert "big_thunder" in visited_ids
```

- [ ] **Step 3: テスト実行（失敗確認）**

Run: `pytest tests/test_router.py -v`
Expected: ImportError

- [ ] **Step 4: `src/router.py` の最小実装**

```python
"""ルート生成（貪欲法 + スコアリング）。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from pydantic import BaseModel

from src.constants import DPA_WAIT_MIN, EXP_VALUE
from src.distance import travel_time_min
from src.models import (
    Attraction, FixedBlock, RouteResult, RouteStep,
    WaitTimeSnapshot, Warning,
)
from src.predictor import predict_wait
from src.scraper import match_attraction_by_scrape_key


class RouteConstraints(BaseModel):
    start_time: datetime
    close_time: datetime
    entrance: tuple[float, float]
    fixed_blocks: list[FixedBlock]


def _is_operating(attraction: Attraction, snapshot: WaitTimeSnapshot) -> bool:
    entry = match_attraction_by_scrape_key(snapshot.data, attraction.scrape_key)
    return entry is not None and entry.status == "operating"


def _current_wait(attraction: Attraction, snapshot: WaitTimeSnapshot) -> int:
    entry = match_attraction_by_scrape_key(snapshot.data, attraction.scrape_key)
    return entry.wait_min if entry and entry.wait_min is not None else 0


def _candidate_pool(
    attractions: Iterable[Attraction],
    snapshot: WaitTimeSnapshot,
    visited: set[str],
) -> list[Attraction]:
    return [
        a for a in attractions
        if a.id not in visited
        and not a.requires_reservation
        and _is_operating(a, snapshot)
    ]


def _score(
    attraction: Attraction,
    current_time: datetime,
    current_location: tuple[float, float],
    current_area: str | None,
    snapshot: WaitTimeSnapshot,
    priority: int,
    fixed_blocks: list[FixedBlock],
    weather_mode: str,
) -> tuple[float, float, float]:
    """スコア・移動時間・予測待ちを返す。"""
    travel = travel_time_min(
        current_location, (attraction.lat, attraction.lng),
        current_time, fixed_blocks, weather_mode,
        area_a=current_area, area_b=attraction.area,
    )
    arrive = current_time + timedelta(minutes=travel)
    wait = predict_wait(
        attraction, _current_wait(attraction, snapshot),
        snapshot.timestamp, arrive, weather_mode,
    )
    cost = travel + wait + attraction.experience_time_min
    weather_value_factor = 0.7 if (weather_mode == "rain" and attraction.outdoor) else 1.0
    score = (priority * EXP_VALUE[attraction.popularity_tier] * weather_value_factor) / max(cost, 1)
    return score, travel, wait


def generate_route(
    snapshot: WaitTimeSnapshot,
    attractions: list[Attraction],
    constraints: RouteConstraints,
    priorities: dict[str, int],
    must_visits: set[str],
    weather_mode: str = "normal",
) -> RouteResult:
    """ルートを生成する。"""
    current_time = constraints.start_time
    current_location = constraints.entrance
    current_area: str | None = None
    visited: set[str] = set()
    must_remaining = set(must_visits)
    steps: list[RouteStep] = []
    warnings: list[Warning] = []

    while current_time < constraints.close_time:
        candidates = _candidate_pool(attractions, snapshot, visited)
        if not candidates:
            break

        pending_must = [c for c in candidates if c.id in must_remaining]
        pool = pending_must if pending_must else candidates

        scored = [
            (_score(
                a, current_time, current_location, current_area,
                snapshot, priorities.get(a.id, 1),
                constraints.fixed_blocks, weather_mode,
            ), a)
            for a in pool
        ]
        (best_score, travel, wait), best = max(scored, key=lambda x: x[0][0])
        cost = travel + wait + best.experience_time_min

        if current_time + timedelta(minutes=cost) > constraints.close_time:
            break

        arrive = current_time + timedelta(minutes=travel)
        ride_start = arrive + timedelta(minutes=wait)
        ride_end = ride_start + timedelta(minutes=best.experience_time_min)

        steps.append(RouteStep(
            type="attraction", id=best.id,
            arrive=arrive, ride_start=ride_start, ride_end=ride_end,
            travel_min=travel, wait_min=wait, via="standby",
            label=best.name,
        ))
        current_time = ride_end
        current_location = (best.lat, best.lng)
        current_area = best.area
        visited.add(best.id)
        must_remaining.discard(best.id)

    return RouteResult(
        steps=steps,
        unvisited_musts=sorted(must_remaining),
        warnings=warnings,
    )
```

- [ ] **Step 5: テスト再実行**

Run: `pytest tests/test_router.py -v`
Expected: 全 PASS

- [ ] **Step 6: コミット**

```bash
git add src/router.py tests/test_router.py tests/conftest.py
git commit -m "feat: minimal route generation with scoring and requires_reservation filter"
```

---

### Task 15: ルーター — must-visit 優先プール

**Files:**
- Modify: `tests/test_router.py`
- Modify: `src/router.py`（必要なら）

- [ ] **Step 1: テスト追加**

```python
# tests/test_router.py に追加

def test_must_visit_consumed_first(sample_attractions, operating_snapshot):
    """must_visits に big_thunder が入っていれば、priority が同じでも先に訪問される。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"big_thunder"},
    )
    visited_ids = [s.id for s in result.steps if s.type == "attraction"]
    # big_thunder が最初
    assert visited_ids[0] == "big_thunder"


def test_unvisited_must_returned(sample_attractions, operating_snapshot):
    """closed のアトラクションを must にした場合、unvisited_musts に残る。"""
    snapshot_with_closed = operating_snapshot.model_copy()
    snapshot_with_closed.data[1].status = "closed"  # big_thunder closed

    result = generate_route(
        snapshot=snapshot_with_closed,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"big_thunder"},
    )
    assert "big_thunder" in result.unvisited_musts
```

- [ ] **Step 2: テスト実行**

Run: `pytest tests/test_router.py::test_must_visit_consumed_first tests/test_router.py::test_unvisited_must_returned -v`
Expected: PASS（Task 14 の実装で既にカバーされているはず）

- [ ] **Step 3: 失敗する場合のみ修正、PASS ならコミット**

```bash
git add tests/test_router.py
git commit -m "test: cover must-visit prioritization and unvisited reporting"
```

---

### Task 16: ルーター — DPA ブロックの取り込み

**Files:**
- Modify: `src/router.py`
- Modify: `tests/test_router.py`

- [ ] **Step 1: テスト追加**

```python
# tests/test_router.py に追加

def test_dpa_block_visits_reserved_attraction(sample_attractions, operating_snapshot):
    """DPA ブロックが指定時間に消化され、requires_reservation のアトラクションが訪問される。"""
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="dpa",
                start=datetime(2026, 5, 25, 10, 30),
                end=datetime(2026, 5, 25, 11, 30),
                label="DPA: 美女と野獣",
                attraction_id="beauty_and_beast",
                location=(35.6336, 139.8808),
            ),
        ],
    )
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"beauty_and_beast"},
    )
    dpa_steps = [s for s in result.steps if s.type == "dpa"]
    assert len(dpa_steps) == 1
    assert dpa_steps[0].id == "beauty_and_beast"
    assert dpa_steps[0].via == "dpa"
    assert dpa_steps[0].wait_min == 15
    assert "beauty_and_beast" not in result.unvisited_musts
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_router.py::test_dpa_block_visits_reserved_attraction -v`
Expected: FAIL — 現状の `generate_route` は `fixed_blocks` を処理していない

- [ ] **Step 3: `src/router.py` を拡張**

`generate_route` の `while` ループを書き換える：

```python
# src/router.py の generate_route を以下に差し替え

def generate_route(
    snapshot: WaitTimeSnapshot,
    attractions: list[Attraction],
    constraints: RouteConstraints,
    priorities: dict[str, int],
    must_visits: set[str],
    weather_mode: str = "normal",
) -> RouteResult:
    """ルートを生成する。"""
    attractions_by_id = {a.id: a for a in attractions}
    current_time = constraints.start_time
    current_location = constraints.entrance
    current_area: str | None = None
    visited: set[str] = set()
    must_remaining = set(must_visits)
    steps: list[RouteStep] = []
    warnings: list[Warning] = []
    blocks = sorted(constraints.fixed_blocks, key=lambda b: b.start)

    while current_time < constraints.close_time:
        # (A) 固定ブロック消化
        if blocks and blocks[0].start <= current_time:
            block = blocks.pop(0)
            step = _handle_fixed_block(block, current_time, current_location, attractions_by_id)
            if step is None:
                warnings.append(Warning(
                    kind="dpa_window_missed",
                    message=f"DPA 窓に間に合わず: {block.label}",
                    attraction_id=block.attraction_id,
                ))
                current_time = block.end
                continue
            steps.append(step)
            current_time = block.end
            if block.location:
                current_location = block.location
            if block.type == "dpa" and block.attraction_id:
                visited.add(block.attraction_id)
                must_remaining.discard(block.attraction_id)
            continue

        # (B) 通常候補
        candidates = _candidate_pool(attractions, snapshot, visited)
        if not candidates:
            break

        pending_must = [c for c in candidates if c.id in must_remaining]
        pool = pending_must if pending_must else candidates

        scored = [
            (_score(
                a, current_time, current_location, current_area,
                snapshot, priorities.get(a.id, 1),
                constraints.fixed_blocks, weather_mode,
            ), a)
            for a in pool
        ]
        (best_score, travel, wait), best = max(scored, key=lambda x: x[0][0])
        cost = travel + wait + best.experience_time_min

        # 次の固定ブロックまでに収まらない場合は弾く
        next_block_start = blocks[0].start if blocks else constraints.close_time
        time_until_block_min = (next_block_start - current_time).total_seconds() / 60
        if cost > time_until_block_min:
            if pending_must:
                warnings.append(Warning(
                    kind="time_conflict",
                    message=f"{best.name} が固定ブロックまでに収まらず",
                    attraction_id=best.id,
                ))
                must_remaining.discard(best.id)
                continue
            # 任意候補のうち、固定ブロックまでに収まるものに絞って再評価
            fit_pool = []
            for a in candidates:
                s, t, w = _score(
                    a, current_time, current_location, current_area,
                    snapshot, priorities.get(a.id, 1),
                    constraints.fixed_blocks, weather_mode,
                )
                if t + w + a.experience_time_min <= time_until_block_min:
                    fit_pool.append(((s, t, w), a))
            if fit_pool:
                (best_score, travel, wait), best = max(fit_pool, key=lambda x: x[0][0])
                cost = travel + wait + best.experience_time_min
            else:
                # 収まる候補なし → 固定ブロック時刻まで current_time を進める
                current_time = next_block_start
                continue

        if current_time + timedelta(minutes=cost) > constraints.close_time:
            break

        arrive = current_time + timedelta(minutes=travel)
        ride_start = arrive + timedelta(minutes=wait)
        ride_end = ride_start + timedelta(minutes=best.experience_time_min)

        steps.append(RouteStep(
            type="attraction", id=best.id,
            arrive=arrive, ride_start=ride_start, ride_end=ride_end,
            travel_min=travel, wait_min=wait, via="standby",
            label=best.name,
        ))
        current_time = ride_end
        current_location = (best.lat, best.lng)
        current_area = best.area
        visited.add(best.id)
        must_remaining.discard(best.id)

    # 終了処理：DPA 予約済みだが消化されなかったブロックも警告に
    for block in blocks:
        if block.type == "dpa" and block.attraction_id:
            warnings.append(Warning(
                kind="dpa_window_missed",
                message=f"DPA 時間内に到達できず: {block.label}",
                attraction_id=block.attraction_id,
            ))

    return RouteResult(
        steps=steps,
        unvisited_musts=sorted(must_remaining),
        warnings=warnings,
    )


def _handle_fixed_block(
    block: FixedBlock,
    current_time: datetime,
    current_location: tuple[float, float],
    attractions_by_id: dict[str, Attraction],
) -> RouteStep | None:
    if block.type == "dpa":
        if not block.attraction_id or not block.location:
            return None
        attraction = attractions_by_id.get(block.attraction_id)
        if attraction is None:
            return None
        travel = travel_time_min(
            current_location, block.location,
            current_time, [], weather_mode="normal",
        )
        arrive = current_time + timedelta(minutes=travel)
        if arrive > block.end:
            return None
        actual_start = max(arrive, block.start)
        wait_min = DPA_WAIT_MIN
        ride_start = actual_start + timedelta(minutes=wait_min)
        ride_end = ride_start + timedelta(minutes=attraction.experience_time_min)
        return RouteStep(
            type="dpa", id=block.attraction_id,
            arrive=arrive, ride_start=ride_start, ride_end=ride_end,
            travel_min=travel, wait_min=wait_min, via="dpa",
            label=block.label,
        )
    if block.type == "meal":
        return RouteStep(
            type="meal", id=block.restaurant_id,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    if block.type == "show":
        return RouteStep(
            type="show", id=None,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    if block.type == "parade":
        return RouteStep(
            type="parade", id=None,
            arrive=block.start, ride_start=block.start, ride_end=block.end,
            travel_min=0, wait_min=0, via=None, label=block.label,
        )
    return None
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_router.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/router.py tests/test_router.py
git commit -m "feat: handle DPA/meal/show/parade fixed blocks in router"
```

---

### Task 17: ルーター — 食事ブロックで current_location が更新される

**Files:**
- Modify: `tests/test_router.py`

- [ ] **Step 1: テスト追加**

```python
# tests/test_router.py に追加

def test_meal_block_anchors_location(sample_attractions, operating_snapshot):
    """食事ブロックに location があれば、ブロック終了後の現在地が更新される。"""
    meal_location = (35.6325, 139.8800)
    constraints = RouteConstraints(
        start_time=datetime(2026, 5, 25, 9, 0),
        close_time=datetime(2026, 5, 25, 21, 0),
        entrance=(35.6329, 139.8804),
        fixed_blocks=[
            FixedBlock(
                type="meal",
                start=datetime(2026, 5, 25, 12, 0),
                end=datetime(2026, 5, 25, 13, 0),
                label="昼食",
                location=meal_location,
            ),
        ],
    )
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=constraints,
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits=set(),
    )
    meal_steps = [s for s in result.steps if s.type == "meal"]
    assert len(meal_steps) == 1
    # 食事後のアトラクション訪問が存在する（=ルートが継続している）
    after_meal = [s for s in result.steps if s.type == "attraction" and s.arrive > meal_steps[0].ride_end]
    assert len(after_meal) > 0
```

- [ ] **Step 2: テスト実行**

Run: `pytest tests/test_router.py::test_meal_block_anchors_location -v`
Expected: PASS（Task 16 で既に対応済み）

- [ ] **Step 3: コミット**

```bash
git add tests/test_router.py
git commit -m "test: verify meal block updates current location"
```

---

### Task 18: ルーター — 雨天モード時の屋外優先度ダウン

**Files:**
- Modify: `tests/test_router.py`

- [ ] **Step 1: テスト追加**

```python
# tests/test_router.py に追加

def test_rain_mode_deprioritizes_outdoor(sample_attractions, operating_snapshot):
    """雨天時、屋外（big_thunder）より屋内（pooh）が先に来やすくなる。"""
    # 同じ priority で並べる
    priorities = {"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5}

    normal = generate_route(
        snapshot=operating_snapshot, attractions=sample_attractions,
        constraints=make_constraints(), priorities=priorities, must_visits=set(),
        weather_mode="normal",
    )
    rain = generate_route(
        snapshot=operating_snapshot, attractions=sample_attractions,
        constraints=make_constraints(), priorities=priorities, must_visits=set(),
        weather_mode="rain",
    )

    normal_first = next(s.id for s in normal.steps if s.type == "attraction")
    rain_first = next(s.id for s in rain.steps if s.type == "attraction")

    # 雨天モード時に屋内（pooh）が優先される
    assert rain_first == "pooh"
```

- [ ] **Step 2: テスト実行**

Run: `pytest tests/test_router.py::test_rain_mode_deprioritizes_outdoor -v`
Expected: PASS（Task 14 のスコア式に weather_value_factor が入っているはず）

- [ ] **Step 3: コミット**

```bash
git add tests/test_router.py
git commit -m "test: verify rain mode deprioritizes outdoor attractions"
```

---

### Task 19: ルーター — `requires_reservation` 未予約 + must の場合の警告

**Files:**
- Modify: `src/router.py`
- Modify: `tests/test_router.py`

- [ ] **Step 1: テスト追加**

```python
# tests/test_router.py に追加

def test_no_dpa_for_reserved_must(sample_attractions, operating_snapshot):
    """must-visit に予約必須アトラクションを入れたが DPA ブロックがない場合、警告が出る。"""
    result = generate_route(
        snapshot=operating_snapshot,
        attractions=sample_attractions,
        constraints=make_constraints(),
        priorities={"pooh": 5, "big_thunder": 5, "beauty_and_beast": 5},
        must_visits={"beauty_and_beast"},
    )
    assert "beauty_and_beast" in result.unvisited_musts
    kinds = [w.kind for w in result.warnings]
    assert "no_dpa_for_reserved" in kinds
```

- [ ] **Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_router.py::test_no_dpa_for_reserved_must -v`
Expected: FAIL — 警告がまだ実装されていない

- [ ] **Step 3: `src/router.py` の return 直前に追加**

```python
# src/router.py の generate_route 内、最後のループの後（return の直前）に追加

    # 予約必須アトラクションを must にしたが DPA ブロックがなかったケース
    dpa_attraction_ids = {b.attraction_id for b in constraints.fixed_blocks if b.type == "dpa"}
    for must_id in must_remaining:
        attraction = attractions_by_id.get(must_id)
        if attraction and attraction.requires_reservation and must_id not in dpa_attraction_ids:
            warnings.append(Warning(
                kind="no_dpa_for_reserved",
                message=f"{attraction.name} は予約必須ですが DPA が登録されていません",
                attraction_id=must_id,
            ))
```

- [ ] **Step 4: テスト再実行**

Run: `pytest tests/test_router.py -v`
Expected: 全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/router.py tests/test_router.py
git commit -m "feat: warn when must-visit requires reservation but no DPA registered"
```

---

## Phase 6：Streamlit UI

UI は仕様書 §11.1 に基づき手動テスト主体。TDD は適用せず、セクション単位で実装 → 起動して動作確認 → コミット の流れ。

### Task 20: app.py の骨組みと設定セクション

**Files:**
- Create: `app.py`

- [ ] **Step 1: 最小骨組みを作成**

```python
# app.py
"""TDL Route Planner Streamlit App."""
from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import streamlit as st

from src.models import Attraction, Restaurant


st.set_page_config(page_title="TDL Route Planner", page_icon="🎢", layout="centered")


@st.cache_data
def load_attractions() -> list[Attraction]:
    raw = json.loads(Path("data/attractions.json").read_text())
    return [
        Attraction.model_validate(a)
        for a in raw["attractions"]
        if a["lat"] is not None and a["lng"] is not None
    ]


@st.cache_data
def load_restaurants() -> list[Restaurant]:
    raw = json.loads(Path("data/restaurants.json").read_text())
    return [
        Restaurant.model_validate(r)
        for r in raw["restaurants"]
        if r["lat"] is not None and r["lng"] is not None
    ]


def _init_session_state():
    defaults = {
        "priorities": {},
        "must_visits": set(),
        "meal_blocks": [],
        "show_blocks": [],
        "dpa_blocks": [],
        "weather_mode": "normal",
        "last_snapshot": None,
        "last_fetch_time": None,
        "current_route": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def main():
    _init_session_state()
    st.title("🎢 TDL Route Planner")
    st.caption(f"📅 {date.today().isoformat()}（設定は本日中だけ自動保存）")

    attractions = load_attractions()
    restaurants = load_restaurants()

    if not attractions:
        st.error("data/attractions.json に座標が埋まったアトラクションがありません。マスタ整備（Phase 3）を完了してください。")
        return

    st.checkbox("☂️ 雨天モード", key="weather_toggle", value=(st.session_state.weather_mode == "rain"))
    st.session_state.weather_mode = "rain" if st.session_state.get("weather_toggle") else "normal"

    st.write(f"アトラクション数：{len(attractions)} 件 / レストラン数：{len(restaurants)} 件")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 起動確認**

Run（別ターミナルで）: `streamlit run app.py`
Expected: ブラウザが開き、タイトルと日付、雨天モードトグル、アトラクション/レストラン数が表示される。座標未整備なら error メッセージが表示される。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: streamlit app skeleton with session state init"
```

---

### Task 21: アトラクション設定セクション（priority + must-visit）

**Files:**
- Modify: `app.py`

- [ ] **Step 1: セクションを追加**

`main()` 関数内、雨天モードトグルの後に追加：

```python
    # アトラクション設定
    with st.expander("▼ アトラクション設定", expanded=False):
        for a in sorted(attractions, key=lambda x: (x.area, x.name)):
            col1, col2 = st.columns([1, 3])
            with col1:
                must = st.checkbox(
                    "必ず乗る",
                    key=f"must_{a.id}",
                    value=(a.id in st.session_state.must_visits),
                )
            with col2:
                priority = st.slider(
                    a.name,
                    min_value=1, max_value=5,
                    value=st.session_state.priorities.get(a.id, a.default_priority),
                    key=f"prio_{a.id}",
                )
            st.session_state.priorities[a.id] = priority
            if must:
                st.session_state.must_visits.add(a.id)
            else:
                st.session_state.must_visits.discard(a.id)
            if a.requires_reservation and must:
                dpa_ids = {b["attraction_id"] for b in st.session_state.dpa_blocks}
                if a.id not in dpa_ids:
                    st.warning(f"⚠️ {a.name} は予約必須です。DPA を登録してください。")
```

- [ ] **Step 2: 起動して操作確認**

Run: `streamlit run app.py`
Expected: アコーディオンを開くとアトラクション一覧、必ず乗る + ★1-5 のスライダーが表示される

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: attraction settings section with priority and must-visit"
```

---

### Task 22: 食事 / ショー / パレード / DPA ブロック入力

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 食事セクションを追加**

`main()` 内、アトラクション設定の後に追加：

```python
    # 食事
    with st.expander("▼ 食事ブロック", expanded=False):
        meal_count = st.number_input("食事の数", min_value=0, max_value=4, value=len(st.session_state.meal_blocks) or 2)
        new_meals = []
        rest_map = {r.id: r for r in restaurants}
        rest_options = ["（未選択）"] + [r.id for r in restaurants]
        for i in range(int(meal_count)):
            cols = st.columns([3, 2, 2])
            existing = st.session_state.meal_blocks[i] if i < len(st.session_state.meal_blocks) else None
            with cols[0]:
                rid = st.selectbox(
                    f"店 #{i+1}",
                    rest_options,
                    format_func=lambda x: "（未選択）" if x == "（未選択）" else rest_map[x].name,
                    index=(rest_options.index(existing["restaurant_id"]) if existing and existing.get("restaurant_id") in rest_options else 0),
                    key=f"meal_rest_{i}",
                )
            with cols[1]:
                start_t = st.time_input(f"開始 #{i+1}", value=(time.fromisoformat(existing["start"]) if existing else time(12, 0)), key=f"meal_start_{i}")
            with cols[2]:
                end_default = time(13, 30) if i == 0 else time(19, 0)
                end_t = st.time_input(f"終了 #{i+1}", value=(time.fromisoformat(existing["end"]) if existing else end_default), key=f"meal_end_{i}")
            if rid != "（未選択）":
                r = rest_map[rid]
                new_meals.append({
                    "restaurant_id": rid,
                    "label": r.name,
                    "start": start_t.isoformat(timespec="minutes"),
                    "end": end_t.isoformat(timespec="minutes"),
                    "lat": r.lat,
                    "lng": r.lng,
                })
        st.session_state.meal_blocks = new_meals

    # ショー / パレード
    with st.expander("▼ ショー・パレード", expanded=False):
        show_count = st.number_input("ショー/パレードの数", min_value=0, max_value=5, value=len(st.session_state.show_blocks))
        new_shows = []
        for i in range(int(show_count)):
            cols = st.columns([3, 2, 2, 2])
            existing = st.session_state.show_blocks[i] if i < len(st.session_state.show_blocks) else None
            with cols[0]:
                label = st.text_input(f"ラベル #{i+1}", value=(existing["label"] if existing else "パレード"), key=f"show_label_{i}")
            with cols[1]:
                start_t = st.time_input(f"開始 #{i+1}", value=(time.fromisoformat(existing["start"]) if existing else time(13, 30)), key=f"show_start_{i}")
            with cols[2]:
                end_t = st.time_input(f"終了 #{i+1}", value=(time.fromisoformat(existing["end"]) if existing else time(14, 15)), key=f"show_end_{i}")
            with cols[3]:
                watch = st.checkbox("鑑賞", value=(existing["watch"] if existing else False), key=f"show_watch_{i}")
            new_shows.append({
                "type": "parade" if "パレード" in label else "show",
                "label": label,
                "start": start_t.isoformat(timespec="minutes"),
                "end": end_t.isoformat(timespec="minutes"),
                "watch": watch,
            })
        st.session_state.show_blocks = new_shows

    # DPA
    with st.expander("▼ DPA 予約", expanded=False):
        attraction_map = {a.id: a for a in attractions}
        dpa_count = st.number_input("DPA 数", min_value=0, max_value=4, value=len(st.session_state.dpa_blocks))
        new_dpa = []
        dpa_options = ["（未選択）"] + [a.id for a in attractions if a.dpa_eligible]
        for i in range(int(dpa_count)):
            cols = st.columns([3, 2, 2])
            existing = st.session_state.dpa_blocks[i] if i < len(st.session_state.dpa_blocks) else None
            with cols[0]:
                aid = st.selectbox(
                    f"アトラクション #{i+1}",
                    dpa_options,
                    format_func=lambda x: "（未選択）" if x == "（未選択）" else attraction_map[x].name,
                    index=(dpa_options.index(existing["attraction_id"]) if existing and existing.get("attraction_id") in dpa_options else 0),
                    key=f"dpa_attr_{i}",
                )
            with cols[1]:
                start_t = st.time_input(f"開始 #{i+1}", value=(time.fromisoformat(existing["start"]) if existing else time(10, 30)), key=f"dpa_start_{i}")
            with cols[2]:
                end_t = st.time_input(f"終了 #{i+1}", value=(time.fromisoformat(existing["end"]) if existing else time(11, 30)), key=f"dpa_end_{i}")
            if aid != "（未選択）":
                a = attraction_map[aid]
                new_dpa.append({
                    "attraction_id": aid,
                    "label": f"DPA: {a.name}",
                    "start": start_t.isoformat(timespec="minutes"),
                    "end": end_t.isoformat(timespec="minutes"),
                    "lat": a.lat,
                    "lng": a.lng,
                })
        st.session_state.dpa_blocks = new_dpa
```

- [ ] **Step 2: 起動して操作確認**

Run: `streamlit run app.py`
Expected: 食事 / ショー / DPA の各セクションが折りたたみ可能、追加・削除が動作する

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: meal/show/parade/DPA block input sections"
```

---

### Task 23: スクレイピング更新 + ルート生成ボタン + 結果表示

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 取得・生成・表示のロジックを追加**

`main()` 関数内、DPA セクションの後に追加：

```python
    # 取得 + 生成
    from src.router import RouteConstraints, generate_route
    from src.scraper import fetch_realtime_wait_times
    from src.models import FixedBlock

    col_fetch, col_gen = st.columns(2)
    with col_fetch:
        if st.button("🔄 更新（待ち時間取得）"):
            with st.spinner("取得中..."):
                snap = fetch_realtime_wait_times()
                if snap:
                    st.session_state.last_snapshot = snap
                    st.session_state.last_fetch_time = datetime.now()
                    st.success(f"取得成功：{snap.timestamp.strftime('%H:%M')}")
                else:
                    st.error("取得に失敗しました")

    with col_gen:
        if st.button("⚡ ルート生成", type="primary"):
            if st.session_state.last_snapshot is None:
                st.warning("先に「更新」を押してください")
            else:
                today = date.today()
                fixed_blocks = []
                for m in st.session_state.meal_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="meal",
                        start=datetime.combine(today, time.fromisoformat(m["start"])),
                        end=datetime.combine(today, time.fromisoformat(m["end"])),
                        label=m["label"],
                        restaurant_id=m["restaurant_id"],
                        location=(m["lat"], m["lng"]),
                    ))
                for s in st.session_state.show_blocks:
                    fixed_blocks.append(FixedBlock(
                        type=s["type"],
                        start=datetime.combine(today, time.fromisoformat(s["start"])),
                        end=datetime.combine(today, time.fromisoformat(s["end"])),
                        label=s["label"],
                        watch=s["watch"],
                    ))
                for d in st.session_state.dpa_blocks:
                    fixed_blocks.append(FixedBlock(
                        type="dpa",
                        start=datetime.combine(today, time.fromisoformat(d["start"])),
                        end=datetime.combine(today, time.fromisoformat(d["end"])),
                        label=d["label"],
                        attraction_id=d["attraction_id"],
                        location=(d["lat"], d["lng"]),
                    ))
                raw = json.loads(Path("data/attractions.json").read_text())
                constraints = RouteConstraints(
                    start_time=datetime.combine(today, time(9, 0)),
                    close_time=datetime.combine(today, time(21, 0)),
                    entrance=(raw["entrance"]["lat"], raw["entrance"]["lng"]),
                    fixed_blocks=fixed_blocks,
                )
                result = generate_route(
                    snapshot=st.session_state.last_snapshot,
                    attractions=attractions,
                    constraints=constraints,
                    priorities=st.session_state.priorities,
                    must_visits=set(st.session_state.must_visits),
                    weather_mode=st.session_state.weather_mode,
                )
                st.session_state.current_route = result

    # 結果表示
    result = st.session_state.current_route
    if result:
        st.subheader("▼ 推奨ルート")
        for s in result.steps:
            icon = {"attraction": "🎢", "meal": "🍴", "show": "🎭", "parade": "🎉", "dpa": "🎟"}[s.type]
            label = s.label or s.id or ""
            line = f"{s.arrive.strftime('%H:%M')} {icon} {label}"
            if s.wait_min:
                line += f"（待ち {int(s.wait_min)} 分）"
            st.write(line)

        if result.unvisited_musts:
            st.warning("⚠️ 未消化の must-visit:\n" + "\n".join(f"- {m}" for m in result.unvisited_musts))

        for w in result.warnings:
            st.warning(f"⚠️ {w.message}")
```

- [ ] **Step 2: 起動確認**

Run: `streamlit run app.py`
Expected: 「更新」でスクレイピング、「ルート生成」でルートが表示される

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: fetch button, route generation, and result display"
```

---

### Task 24: localStorage 永続化

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 永続化ロジックを追加**

`main()` の冒頭、`_init_session_state()` の直後に追加：

```python
    from streamlit_local_storage import LocalStorage

    storage = LocalStorage()
    today_key = f"tdl_settings_{date.today().isoformat()}"

    # 起動時にロード
    if not st.session_state.get("_loaded"):
        saved_raw = storage.getItem(today_key)
        if saved_raw:
            try:
                saved = json.loads(saved_raw) if isinstance(saved_raw, str) else saved_raw
                for k, v in saved.items():
                    if k == "must_visits":
                        st.session_state[k] = set(v)
                    else:
                        st.session_state[k] = v
            except Exception:
                pass
        st.session_state._loaded = True
```

`main()` の最後（return / 関数末尾の直前）に追加：

```python
    # 都度保存
    to_save = {
        "priorities": st.session_state.priorities,
        "must_visits": list(st.session_state.must_visits),
        "meal_blocks": st.session_state.meal_blocks,
        "show_blocks": st.session_state.show_blocks,
        "dpa_blocks": st.session_state.dpa_blocks,
        "weather_mode": st.session_state.weather_mode,
    }
    storage.setItem(today_key, json.dumps(to_save, ensure_ascii=False))
```

- [ ] **Step 2: 起動して動作確認**

Run: `streamlit run app.py`

確認手順：
1. 優先度を変更、must-visit をチェック
2. タブを閉じる
3. 同じ URL を開き直す → 設定が復元される

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: localStorage persistence scoped by date key"
```

---

### Task 25: CSV 出力

**Files:**
- Modify: `app.py`

- [ ] **Step 1: CSV ダウンロードボタン追加**

結果表示の最後に追加：

```python
    if result:
        import pandas as pd
        df = pd.DataFrame([
            {
                "時刻": s.arrive.strftime("%H:%M"),
                "種別": s.type,
                "名前": s.label or s.id or "",
                "待ち分": int(s.wait_min) if s.wait_min else 0,
                "移動分": int(s.travel_min) if s.travel_min else 0,
            }
            for s in result.steps
        ])
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 CSV 出力", data=csv, file_name=f"route_{date.today().isoformat()}.csv", mime="text/csv")
```

- [ ] **Step 2: 起動確認**

Run: `streamlit run app.py`
Expected: ルート生成後、CSV ダウンロードボタンから CSV が落ちる

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: CSV export for generated route"
```

---

## Phase 7：デプロイ

### Task 26: requirements.txt と README

**Files:**
- Create: `requirements.txt`
- Create: `README.md`

- [ ] **Step 1: `requirements.txt` を生成**

```
streamlit>=1.36
requests>=2.32
beautifulsoup4>=4.12
pydantic>=2.7
geopy>=2.4
pandas>=2.2
streamlit-local-storage>=0.0.21
```

- [ ] **Step 2: `README.md` を作成**

```markdown
# TDL Route Planner

東京ディズニーランド来園日に使う、個人用のリアルタイムルート生成ツール。

## 利用目的
- 個人学習目的、非商用
- Disney / OLC 商標は使用しない

## ローカル起動
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

## マスタ整備
1. `python scripts/generate_attractions_template.py`
2. `python scripts/generate_restaurants_template.py`
3. `data/attractions.json` と `data/restaurants.json` の `lat`/`lng` を Google マップで手動測定して埋める
4. `pytest tests/test_masters.py -v` で全 PASS を確認

## テスト
```bash
pytest -v
```

## デプロイ（Streamlit Community Cloud）
1. GitHub に public リポジトリとして push
2. https://share.streamlit.io/ で New app
3. リポジトリ・ブランチ・`app.py` を指定して deploy
```

- [ ] **Step 3: コミット**

```bash
git add requirements.txt README.md
git commit -m "docs: add README and requirements.txt for Streamlit Cloud"
```

---

### Task 27: GitHub リポジトリ作成 + Streamlit Cloud デプロイ

**Files:** なし（インフラ作業）

- [ ] **Step 1: GitHub に public リポジトリを作成**

東郷さんへ：
1. GitHub で `tdl-route-planner`（または好きな名前）リポジトリを作成（public）
2. ローカルから push：

```bash
git remote add origin https://github.com/<your_username>/tdl-route-planner.git
git branch -M main
git push -u origin main
```

- [ ] **Step 2: Streamlit Community Cloud で deploy**

1. https://share.streamlit.io/ にアクセス
2. GitHub アカウントでログイン
3. "New app" → リポジトリ選択 → branch=main, file=app.py
4. Deploy

- [ ] **Step 3: スマホブラウザで動作確認**

東郷さんへ：発行された URL をスマホで開いて以下を確認：
- アトラクション設定が縦スクロールで操作できるか
- 「更新」「ルート生成」が動くか
- localStorage 永続化が動くか（タブ閉じて再オープン）

---

## 最終チェック（来園日前日：5/24）

### Task 28: 統合テスト

- [ ] **Step 1: 全テスト実行**

Run: `pytest -v`
Expected: 全 PASS

- [ ] **Step 2: 当日リハーサル**

東郷さんへ：
1. スマホでアプリを開く
2. 当日想定の優先度・食事・パレード時刻・DPA を入力
3. 「更新」→「ルート生成」
4. ルートが妥当か目視確認
5. 雨天モードトグル動作確認

- [ ] **Step 3: 営業時間・パレード時刻を公式サイトで確認**

公式サイトで 2026-05-25 の営業時間とパレード時刻を確認し、必要なら `src/constants.py` の `OPEN_TIME` / `CLOSE_TIME` を調整して push。

---

## 完了条件

- [ ] 全 Phase のタスクが checked
- [ ] `pytest -v` が全 PASS
- [ ] スマホブラウザから本番 URL にアクセスでき、ルート生成が動作
- [ ] localStorage 永続化が動作
- [ ] 雨天モード、DPA 入力、must-visit 警告が動作
