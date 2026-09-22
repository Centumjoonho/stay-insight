from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.imports import Channel, ReservationStatus


class ColumnMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_reservation_id: str = Field(min_length=1, max_length=100)
    check_in: str = Field(min_length=1, max_length=100)
    check_out: str = Field(min_length=1, max_length=100)
    gross_revenue: str = Field(min_length=1, max_length=100)
    channel_fee: str | None = None
    guest_count: str | None = None
    reservation_status: str | None = None


class RowError(BaseModel):
    row: int
    field: str
    message: str


class PreviewResponse(BaseModel):
    encoding: str
    headers: list[str]
    rows: list[list[str]]
    total_rows: int
    warnings: list[str]


class ValidationResponse(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[RowError]
    errors_truncated: bool
    warnings: list[str]


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    property_id: UUID
    channel: Channel
    original_filename: str
    file_checksum: str
    status: str
    total_rows: int
    imported_rows: int
    rejected_rows: int
    inserted_rows: int
    updated_rows: int
    created_by_user_id: UUID
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None
    validation_errors: list[RowError]
    column_mapping: dict[str, str]
    adapter_version: str
    duplicate: bool = False


class ImportList(BaseModel):
    items: list[ImportResponse]
    total: int


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    property_id: UUID
    import_id: UUID
    channel: Channel
    external_reservation_id: str
    check_in: date
    check_out: date
    booked_nights: int
    guest_count: int | None
    gross_revenue: Decimal
    channel_fee: Decimal | None
    net_revenue: Decimal | None
    reservation_status: ReservationStatus
    created_at: datetime
    updated_at: datetime
    source: str = "owner_csv"
    net_revenue_method: str = "gross_minus_reported_channel_fee"


class ReservationList(BaseModel):
    items: list[ReservationResponse]
    total: int
