from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard import Comparison, DashboardProperty, DataQuality, Metrics, TrendRow


class InventoryQuality(DataQuality):
    missing_room_units_count: int
    capacity_fallback_days: int
    unrecorded_unavailability_days: int
    overcapacity_days: int


class ProvenanceV2(BaseModel):
    calculation_version: Literal["dashboard-v2"] = "dashboard-v2"
    source: Literal["owner"] = "owner"
    revenue_source: Literal["owner_reservations"] = "owner_reservations"
    expense_source: Literal["MANUAL"] = "MANUAL"
    financial_date_basis: Literal["check_in"] = "check_in"
    operational_date_basis: Literal["overlapping_nights"] = "overlapping_nights"
    allocation_method: Literal["gross_times_overlap_divided_by_booked_nights"] = (
        "gross_times_overlap_divided_by_booked_nights"
    )
    estimated_metrics: list[str] = Field(
        default_factory=lambda: [
            "occupied_room_nights",
            "occupancy_rate",
            "allocated_operational_revenue",
            "adr",
            "revpar",
        ]
    )
    room_units_basis: Literal["reported_or_estimated_one"] = "reported_or_estimated_one"
    inventory_basis: Literal["effective_capacity_minus_unavailable"] = (
        "effective_capacity_minus_unavailable"
    )
    coverage: Literal["recorded_data_only"] = "recorded_data_only"
    generated_at: datetime


class MetricsV2(Metrics):
    data_quality: InventoryQuality


class DashboardSummaryV2(MetricsV2):
    property: DashboardProperty
    metadata: ProvenanceV2
    comparisons: dict[str, Comparison]


class TrendRowV2(TrendRow):
    data_quality: InventoryQuality


class DashboardTrendsV2(BaseModel):
    property: DashboardProperty
    metadata: ProvenanceV2
    items: list[TrendRowV2]
