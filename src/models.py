"""Pydantic モデル定義。"""
from datetime import datetime, time
from typing import Literal, Optional

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
    default_priority: int = Field(ge=0, le=5)
    pass_type: Optional[Literal["dpa", "priority"]] = None
    requires_reservation: bool = False
    outdoor: bool = False
    popularity_tier: PopularityTier
    # Queue-Times.com の ride id（5/22 時点）。null = 未収録
    queue_times_id: int | None = None
    # Queue-Times stats の全期間平均待ち時間（分）。シミュ snapshot で使う。
    # null = stats 未収録（長期休止アトラクション等）→ tier ベースフォールバック
    avg_wait_min: int | None = None


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
    queue_times_id: int | None = None  # Queue-Times.com の ride id


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
    kind: Literal[
        "time_conflict",
        "dpa_window_missed",
        "no_dpa_for_reserved",
        "not_operating",
    ]
    message: str
    attraction_id: str | None = None


class RouteResult(BaseModel):
    steps: list[RouteStep]
    unvisited_musts: list[str]
    warnings: list[Warning]
