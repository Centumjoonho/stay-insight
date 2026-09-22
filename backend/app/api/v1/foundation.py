from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies.tenant import CurrentUser, Database, OrganizationContext
from app.schemas.foundation import (
    MeResponse,
    OnboardingRequest,
    OrganizationResponse,
    PropertyCreate,
    PropertyListResponse,
    PropertyPatch,
    PropertyResponse,
)
from app.services import foundation as service

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def me(db: Database, user: CurrentUser) -> MeResponse:
    return service.current_context(db, user.user_id)


@router.post("/onboarding", response_model=OrganizationResponse)
def onboarding(body: OnboardingRequest, db: Database, user: CurrentUser) -> OrganizationResponse:
    return OrganizationResponse.model_validate(service.onboard(db, user.user_id, body))


@router.post("/properties", response_model=PropertyResponse, status_code=201)
def create_property(
    body: PropertyCreate,
    db: Database,
    org_id: OrganizationContext,
) -> PropertyResponse:
    return PropertyResponse.model_validate(service.create_property(db, org_id, body))


@router.get("/properties", response_model=PropertyListResponse)
def list_properties(
    db: Database,
    org_id: OrganizationContext,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PropertyListResponse:
    return service.list_properties(db, org_id, limit, offset)


@router.get("/properties/{property_id}", response_model=PropertyResponse)
def property_detail(
    property_id: UUID,
    db: Database,
    org_id: OrganizationContext,
) -> PropertyResponse:
    return PropertyResponse.model_validate(service.get_property(db, org_id, property_id))


@router.patch("/properties/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: UUID,
    body: PropertyPatch,
    db: Database,
    org_id: OrganizationContext,
) -> PropertyResponse:
    return PropertyResponse.model_validate(service.update_property(db, org_id, property_id, body))
