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
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(data['attractions'])} attractions to {out}")


if __name__ == "__main__":
    main()
