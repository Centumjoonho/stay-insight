from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

InventoryDate = Annotated[date, Field(ge=date(1901, 1, 1), le=date(9998, 12, 31))]
Units = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class CapacityValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: InventoryDate
    effective_to: InventoryDate | None = None
    inventory_units: Units

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("종료일은 시작일 이후여야 합니다.")
        return self


class CapacityResponse(CapacityValues):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class AvailabilityValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unavailable_units: int = Field(strict=True, ge=0, le=2147483647)
    reason: Literal["MAINTENANCE", "OWNER_BLOCK", "SALES_STOP", "OTHER"]
    memo: str | None = Field(default=None, max_length=1000)


class AvailabilityResponse(AvailabilityValues):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date: date
    created_at: datetime
    updated_at: datetime


class AvailabilityDay(BaseModel):
    date: date
    base_capacity: int
    unavailable_units: int
    available_units: int
    capacity_source: Literal["history", "estimated_property_default"]
    override: AvailabilityResponse | None
