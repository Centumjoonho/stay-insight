from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.foundation import AccommodationType, Role

Name = Annotated[str, Field(min_length=1, max_length=200)]
Address = Annotated[str, Field(min_length=1, max_length=500)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OnboardingRequest(InputModel):
    organization_name: Name


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class MembershipResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    role: Role


class MeResponse(BaseModel):
    user_id: UUID
    memberships: list[MembershipResponse]


class PropertyCreate(InputModel):
    name: Name
    address: Address
    road_address: Annotated[str, Field(max_length=500)] | None = None
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)] | None = None
    accommodation_type: AccommodationType
    inventory_units: Annotated[int, Field(ge=1, le=2147483647, strict=True)]
    timezone: Literal["Asia/Seoul"] = "Asia/Seoul"

    @model_validator(mode="after")
    def coordinates_pair(self) -> "PropertyCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both latitude and longitude must be supplied together")
        return self


class PropertyPatch(InputModel):
    name: Name | None = None
    address: Address | None = None
    road_address: Annotated[str, Field(max_length=500)] | None = None
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)] | None = None
    accommodation_type: AccommodationType | None = None
    inventory_units: Annotated[int, Field(ge=1, le=2147483647, strict=True)] | None = None
    timezone: Literal["Asia/Seoul"] | None = None

    @model_validator(mode="after")
    def non_nullable_fields(self) -> "PropertyPatch":
        if not self.model_fields_set:
            raise ValueError("At least one change is required")
        for field in self.model_fields_set - {"road_address", "latitude", "longitude"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PropertyResponse(PropertyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
