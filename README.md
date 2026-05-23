# Route Planner (Personal Tool)

個人の遊園地来園日に使う、ルート自動生成ツールの試作。
**個人学習目的・非商用利用限定**。

## 概要

- ライブ待ち時間データ（[Queue-Times.com](https://queue-times.com/) の集約 API、5 分毎更新）からアトラクション巡回ルートを生成
- 「必ず乗る」「優先度」「予約済みパス」「食事」「ショー観賞」を入力 → 待ち時間予測 + 移動距離込みで最適化
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
