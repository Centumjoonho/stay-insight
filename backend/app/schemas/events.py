from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.providers.events import DATASET, SOURCE_URL


class EventItem(BaseModel):
    source_event_id: str
    title: str
    start_date: date
    end_date: date
    temporal_status: Literal["ONGOING", "UPCOMING", "PAST"]
    address: str | None
    source_status: str | None
    last_seen_at: datetime


class EventScope(BaseModel):
    level: Literal["SIGUNGU"] = "SIGUNGU"
    name: str


class EventSource(BaseModel):
    provider: str = "한국관광공사"
    dataset: str = DATASET
    url: str = SOURCE_URL
    collected_at: datetime | None = None
    latest_sync_status: str | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None


class EventSummary(BaseModel):
    ongoing_count: int | None = None
    next_30_days_count: int | None = None


class EventMarket(BaseModel):
    property_id: UUID
    available: bool = False
    reason: str | None = None
    scope: EventScope | None = None
    from_date: date
    to_date: date
    reference_date: date
    events: list[EventItem] = Field(default_factory=list)
    total_count: int | None = None
    truncated: bool = False
    summary: EventSummary = Field(default_factory=EventSummary)
    source: EventSource = Field(default_factory=EventSource)
    warnings: list[str] = Field(default_factory=list)
    source_category: Literal["public"] = "public"
