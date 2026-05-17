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
