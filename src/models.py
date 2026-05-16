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
