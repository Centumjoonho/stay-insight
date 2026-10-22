from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.imports import Channel, ReservationStatus
from app.reservation_fields import ReservationField

Money = Annotated[
    Decimal, Field(ge=0, le=999999999999999999, decimal_places=0, allow_inf_nan=False)
]
Count = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
BusinessDate = Annotated[date, Field(ge=date(1901, 1, 1), le=date(9998, 12, 31))]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ReservationValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_in: BusinessDate
    check_out: BusinessDate
    gross_revenue: Money
    channel_fee: Money | None = None
    guest_count: Count | None = None
    room_units: Count | None = None
    reservation_status: ReservationStatus = ReservationStatus.UNKNOWN

    @model_validator(mode="after")
    def consistent(self) -> "ReservationValues":
        if self.check_out <= self.check_in:
            raise ValueError("체크아웃은 체크인 이후여야 합니다.")
        if self.channel_fee is not None and self.channel_fee > self.gross_revenue:
            raise ValueError("수수료는 총 매출을 초과할 수 없습니다.")
        return self


class ManualCreate(ReservationValues):
    channel: Channel
    external_reservation_id: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
        | None
    ) = None


class ManualUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    change_reason: Reason
    check_in: BusinessDate | None = None
    check_out: BusinessDate | None = None
    gross_revenue: Money | None = None
    channel_fee: Money | None = None
    guest_count: Count | None = None
    room_units: Count | None = None
    reservation_status: ReservationStatus | None = None


class ReleaseOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    change_reason: Reason
    fields: list[ReservationField] = Field(min_length=1, max_length=7)


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    change_source: str
    actor_subject: UUID
    reservation_import_id: UUID | None
    reason: str | None
    changed_fields: list[str]
    before_values: dict[str, object]
    after_values: dict[str, object]
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditResponse]
    total: int
