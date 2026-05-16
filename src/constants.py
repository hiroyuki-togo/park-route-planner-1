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
