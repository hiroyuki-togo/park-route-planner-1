"""TDL アトラクションマスタの雛形を生成する。
lat/lng は null で出力、後で人力で埋める。
pass_type は "dpa" / "priority" / None のいずれか。雛形は基本 None で、DPA 対象は "dpa" を明示する。

⚠️ 再実行禁止: data/attractions.json が既に存在する場合は abort する。
  既存のマスタには lat/lng / queue_times_id / avg_wait_min が手動投入されており、
  かつ priority 系アトラクションの最新マッピング（pooh / monsters_inc 等）も
  反映されているため、誤って再実行すると現行マスタが壊滅する。
  どうしても上書きしたい場合は環境変数 FORCE_OVERWRITE=1 を指定。"""
import json
import os
import sys
from pathlib import Path


# タプル末尾の項目は pass_type（"dpa" / "priority" / None）
ATTRACTIONS = [
    # ファンタジーランド
    ("beauty_and_beast", "美女と野獣\"魔法のものがたり\"", "美女と野獣", "ファンタジーランド", 7, "S", "dpa", True, False),
    ("pooh", "プーさんのハニーハント", "プーさん", "ファンタジーランド", 5, "S", "dpa", False, False),
    ("peter_pan", "ピーターパン空の旅", "ピーターパン", "ファンタジーランド", 3, "A", None, False, False),
    ("haunted_mansion", "ホーンテッドマンション", "ホーンテッドマンション", "ファンタジーランド", 10, "A", None, False, False),
    ("its_a_small_world", "イッツ・ア・スモールワールド", "スモールワールド", "ファンタジーランド", 10, "B", None, False, False),
    ("snow_white", "白雪姫と七人のこびと", "白雪姫", "ファンタジーランド", 2, "A", None, False, False),
    # トゥモローランド
    ("monsters_inc", "モンスターズ・インク \"ライド&ゴーシーク!\"", "モンスターズ・インク", "トゥモローランド", 4, "S", "dpa", False, False),
    ("buzz", "バズ・ライトイヤーのアストロブラスター", "バズ", "トゥモローランド", 4, "A", None, False, False),
    ("baymax", "ベイマックスのハッピーライド", "ベイマックス", "トゥモローランド", 2, "S", "dpa", False, True),
    # トゥーンタウン
    ("minnie_style", "ミニーのスタイルスタジオ", "ミニーのスタイル", "トゥーンタウン", 5, "B", None, False, False),
    ("roger_rabbit", "ロジャーラビットのカートゥーンスピン", "ロジャーラビット", "トゥーンタウン", 4, "B", None, False, False),
    # ウエスタンランド
    ("big_thunder", "ビッグサンダー・マウンテン", "ビッグサンダー", "ウエスタンランド", 4, "A", None, False, True),
    ("mark_twain", "蒸気船マークトウェイン号", "マークトウェイン", "ウエスタンランド", 12, "C", None, False, True),
    ("country_bear", "カントリーベア・シアター", "カントリーベア", "ウエスタンランド", 15, "C", None, False, False),
    # クリッターカントリー（スプラッシュ閉鎖後の現存アトラクションのみ）
    ("beaver_brothers", "ビーバーブラザーズのカヌー探険", "ビーバーブラザーズ", "クリッターカントリー", 12, "C", None, False, True),
    # アドベンチャーランド
    ("jungle_cruise", "ジャングルクルーズ", "ジャングルクルーズ", "アドベンチャーランド", 10, "B", None, False, True),
    ("pirates", "カリブの海賊", "カリブの海賊", "アドベンチャーランド", 15, "A", None, False, False),
    ("western_river", "ウエスタンリバー鉄道", "ウエスタンリバー", "アドベンチャーランド", 15, "C", None, False, True),
    ("swiss_family", "スイスファミリー・ツリーハウス", "ツリーハウス", "アドベンチャーランド", 10, "C", None, False, True),
    ("enchanted_tiki", "魅惑のチキルーム", "チキルーム", "アドベンチャーランド", 10, "C", None, False, False),
    # ワールドバザール（アトラクションは少なめ）
    ("omnibus", "オムニバス", "オムニバス", "ワールドバザール", 5, "C", None, False, True),
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
                "pass_type": pass_type,
                "requires_reservation": reserve,
                "outdoor": outdoor,
                "popularity_tier": tier,
            }
            for id_, name, key, area, exp, tier, pass_type, reserve, outdoor in ATTRACTIONS
        ],
    }
    out = Path("data/attractions.json")
    if out.exists() and os.environ.get("FORCE_OVERWRITE") != "1":
        sys.exit(
            f"❌ {out} が既に存在します。雛形再生成は現行マスタを壊滅させるため abort します。\n"
            f"   どうしても上書きしたい場合: FORCE_OVERWRITE=1 python {sys.argv[0]}"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(data['attractions'])} attractions to {out}")


if __name__ == "__main__":
    main()
