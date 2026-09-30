from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MarketRegion(BaseModel):
    scope_level: Literal["SIGUNGU"] = "SIGUNGU"
    scope_name: str
    assignment_method: Literal["EXPLICIT_SELECTION"] = "EXPLICIT_SELECTION"


class MarketMetrics(BaseModel):
    open_businesses: int
    new_licenses_12m: int | None
    closures_12m: int | None
    type_breakdown: dict[str, int]
    unknown_status_count: int
    missing_license_dates: int
    missing_closure_dates: int


class MarketFreshness(BaseModel):
    source: str
    source_dataset_name: str
    source_url: str
    collected_at: datetime | None = None
    source_reference_date: date | None = None
    latest_sync_status: str | None = None
    stale: bool = False
    stale_after_days: int = 7
    live_provider_verified: bool = False


class AccommodationMarket(BaseModel):
    property_id: UUID
    region: MarketRegion | None = None
    reference_date: date
    window_start: date
    window_end: date
    market_context_available: bool = False
    reason: str | None = None
    metrics: MarketMetrics | None = None
    freshness: MarketFreshness
    warnings: list[str] = Field(default_factory=list)
    source_category: Literal["public"] = "public"
    calculation_version: Literal["license-market-v1"] = "license-market-v1"
