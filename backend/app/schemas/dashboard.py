from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.expenses import CategoryTotal


class Period(BaseModel):
    month: str
    start_date: date
    end_date: date
    is_current_month: bool
    is_partial: bool


class DashboardProperty(BaseModel):
    id: UUID
    name: str
    inventory_units: int


class Financial(BaseModel):
    recognized_gross_revenue: Decimal
    manual_expense_total: Decimal
    fixed_expense_total: Decimal
    variable_expense_total: Decimal
    known_channel_fee_total: Decimal
    known_cost_total: Decimal
    known_operating_profit: Decimal
    known_operating_margin: Decimal | None


class Operations(BaseModel):
    reservation_count: int
    occupied_room_nights: int
    available_room_nights: int
    occupancy_rate: Decimal | None
    allocated_operational_revenue: Decimal
    adr: Decimal | None
    revpar: Decimal | None
    average_length_of_stay: Decimal | None
    overlapping_reservation_count: int


class Warning(BaseModel):
    code: str
    message: str


class DataQuality(BaseModel):
    unknown_status_count: int
    overlapping_unknown_status_count: int
    cancelled_reservation_count: int
    channel_fee_known_count: int
    channel_fee_missing_count: int
    expense_count: int
    has_financial_reservations: bool
    has_operational_reservations: bool
    warnings: list[Warning]


class ChannelRow(BaseModel):
    channel: str
    reservation_count: int
    recognized_gross_revenue: Decimal
    known_channel_fee: Decimal | None
    channel_fee_known_count: int
    channel_fee_missing_count: int
    booked_nights: int
    revenue_share_percent: Decimal | None


class Metrics(BaseModel):
    period: Period
    financial: Financial
    operations: Operations
    data_quality: DataQuality
    channels: list[ChannelRow]
    category_breakdown: list[CategoryTotal]


class Delta(BaseModel):
    available: bool
    absolute_delta: Decimal | None
    percentage_change: Decimal | None
    percentage_points: Decimal | None


class Comparison(BaseModel):
    period: Period
    metrics: dict[str, Delta]


class Provenance(BaseModel):
    calculation_version: Literal["dashboard-v1"] = "dashboard-v1"
    source: Literal["owner"] = "owner"
    revenue_source: Literal["owner_csv"] = "owner_csv"
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
    room_units_per_reservation: Literal[1] = 1
    inventory_basis: Literal["current_registered_calendar_inventory"] = (
        "current_registered_calendar_inventory"
    )
    coverage: Literal["recorded_data_only"] = "recorded_data_only"
    generated_at: datetime


class DashboardSummary(Metrics):
    property: DashboardProperty
    metadata: Provenance
    comparisons: dict[str, Comparison]


class TrendRow(BaseModel):
    month: str
    end_date: date
    is_partial: bool
    recognized_gross_revenue: Decimal
    manual_expense_total: Decimal
    known_channel_fee_total: Decimal
    known_cost_total: Decimal
    known_operating_profit: Decimal
    occupancy_rate: Decimal | None
    adr: Decimal | None
    revpar: Decimal | None
    reservation_count: int
    has_financial_reservations: bool
    has_operational_reservations: bool
    expense_count: int


class DashboardTrends(BaseModel):
    property: DashboardProperty
    metadata: Provenance
    items: list[TrendRow]
