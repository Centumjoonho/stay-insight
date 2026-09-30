from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.context import set_context
from app.models.foundation import Organization, Property, Role
from app.repositories import foundation as repo
from app.repositories import regions as region_repo
from app.schemas.foundation import (
    MembershipResponse,
    MeResponse,
    OnboardingRequest,
    PropertyCreate,
    PropertyListResponse,
    PropertyPatch,
    PropertyResponse,
)
from app.schemas.regions import RegionResponse
from app.services.regions import validate_region


def current_context(db: Session, user_id: UUID) -> MeResponse:
    return MeResponse(
        user_id=user_id,
        memberships=[
            MembershipResponse(
                organization_id=org.id, organization_name=org.name, role=Role(member.role)
            )
            for member, org in repo.user_memberships(db, user_id)
        ],
    )


def onboard(db: Session, user_id: UUID, body: OnboardingRequest) -> Organization:
    repo.lock_onboarding(db, user_id)
    existing = repo.user_memberships(db, user_id)
    if existing:
        if len(existing) == 1:
            member, org = existing[0]
            if member.role == "OWNER" and org.name == body.organization_name:
                return org
        raise HTTPException(409, "Onboarding already completed")
    organization = Organization(id=uuid4(), name=body.organization_name)
    set_context(db, "app.new_organization_id", organization.id)
    repo.insert_organization(db, organization)
    repo.insert_owner(db, organization.id, user_id)
    return organization


def authorize_organization(db: Session, user_id: UUID, organization_id: UUID) -> UUID:
    if repo.membership(db, user_id, organization_id) is None:
        raise HTTPException(403, "Organization membership required")
    set_context(db, "app.organization_id", organization_id)
    return organization_id


def create_property(db: Session, org_id: UUID, body: PropertyCreate) -> Property:
    validate_region(db, body.region_id)
    return repo.insert_property(db, Property(organization_id=org_id, **body.model_dump()))


def get_property(db: Session, org_id: UUID, property_id: UUID) -> Property:
    item = repo.get_property(db, org_id, property_id)
    if item is None:
        raise HTTPException(404, "Property not found")
    return item


def list_properties(db: Session, org_id: UUID, limit: int, offset: int) -> PropertyListResponse:
    items, total = repo.list_properties(db, org_id, limit, offset)
    regions = {r.id: RegionResponse.model_validate(r) for r in region_repo.supported_regions(db)}
    return PropertyListResponse(
        items=[
            PropertyResponse.model_validate(item).model_copy(
                update={"region": regions.get(item.region_id) if item.region_id else None}
            )
            for item in items
        ],
        total=total,
    )


def update_property(
    db: Session,
    org_id: UUID,
    property_id: UUID,
    body: PropertyPatch,
) -> Property:
    item = get_property(db, org_id, property_id)
    merged = PropertyCreate.model_validate(item, from_attributes=True).model_dump()
    changes = body.model_dump(exclude_unset=True)
    try:
        PropertyCreate.model_validate(merged | changes)
    except ValidationError as error:
        raise HTTPException(422, "Invalid property values or coordinate pair") from error
    if "region_id" in body.model_fields_set:
        validate_region(db, body.region_id)
    updated = repo.save_property(db, org_id, property_id, changes)
    if updated is None:
        raise HTTPException(404, "Property not found")
    return updated


def property_response(db: Session, item: Property) -> PropertyResponse:
    result = PropertyResponse.model_validate(item)
    if item.region_id:
        region = region_repo.supported_region(db, item.region_id)
        result.region = RegionResponse.model_validate(region) if region else None
    return result
