from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies.tenant import CurrentUser, Database, OrganizationContext
from app.schemas.imports import ReservationResponse
from app.schemas.reservations import AuditList, ManualCreate, ManualUpdate, ReleaseOverrides
from app.services import reservations as service

router = APIRouter()


@router.post("/properties/{property_id}/reservations", response_model=ReservationResponse)
def create(
    property_id: UUID, body: ManualCreate, db: Database, org: OrganizationContext, user: CurrentUser
) -> ReservationResponse:
    return service.create(db, org, user.user_id, property_id, body)


@router.patch("/reservations/{reservation_id}", response_model=ReservationResponse)
def update(
    reservation_id: UUID,
    body: ManualUpdate,
    db: Database,
    org: OrganizationContext,
    user: CurrentUser,
) -> ReservationResponse:
    return service.update(db, org, user.user_id, reservation_id, body)


@router.post("/reservations/{reservation_id}/release-overrides", response_model=ReservationResponse)
def release(
    reservation_id: UUID,
    body: ReleaseOverrides,
    db: Database,
    org: OrganizationContext,
    user: CurrentUser,
) -> ReservationResponse:
    return service.release(db, org, user.user_id, reservation_id, body)


@router.get("/reservations/{reservation_id}/history", response_model=AuditList)
def history(
    reservation_id: UUID,
    db: Database,
    org: OrganizationContext,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> AuditList:
    return service.history(db, org, reservation_id, limit, offset)
