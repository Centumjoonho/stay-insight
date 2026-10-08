from datetime import date
from uuid import UUID

from fastapi import APIRouter, Response

from app.api.dependencies.tenant import Database, OrganizationContext
from app.schemas.inventory import (
    AvailabilityDay,
    AvailabilityResponse,
    AvailabilityValues,
    CapacityResponse,
    CapacityValues,
)
from app.services import inventory as service

router = APIRouter(prefix="/properties/{property_id}", tags=["inventory"])


@router.get("/capacity", response_model=list[CapacityResponse])
def capacity(db: Database, org: OrganizationContext, property_id: UUID) -> object:
    return service.list_capacity(db, org, property_id)


@router.post("/capacity", response_model=CapacityResponse)
def create_capacity(
    db: Database, org: OrganizationContext, property_id: UUID, body: CapacityValues
) -> object:
    return service.save_capacity(db, org, property_id, body)


@router.patch("/capacity/{item_id}", response_model=CapacityResponse)
def edit_capacity(
    db: Database, org: OrganizationContext, property_id: UUID, item_id: UUID, body: CapacityValues
) -> object:
    return service.save_capacity(db, org, property_id, body, item_id)


@router.delete("/capacity/{item_id}", status_code=204)
def delete_capacity(
    db: Database, org: OrganizationContext, property_id: UUID, item_id: UUID
) -> Response:
    service.delete_capacity(db, org, property_id, item_id)
    return Response(status_code=204)


@router.get("/availability", response_model=list[AvailabilityDay])
def availability(
    db: Database, org: OrganizationContext, property_id: UUID, start: date, end: date
) -> object:
    return service.availability(db, org, property_id, start, end)


@router.post("/availability/{day}", response_model=AvailabilityResponse)
def save_availability(
    db: Database, org: OrganizationContext, property_id: UUID, day: date, body: AvailabilityValues
) -> object:
    return service.save_override(db, org, property_id, day, body)


@router.delete("/availability/{day}", status_code=204)
def delete_availability(
    db: Database, org: OrganizationContext, property_id: UUID, day: date
) -> Response:
    service.delete_override(db, org, property_id, day)
    return Response(status_code=204)
