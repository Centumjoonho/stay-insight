from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies.tenant import Database, OrganizationContext
from app.schemas.market import AccommodationMarket
from app.schemas.visitors import VisitorMarket
from app.services import market as service
from app.services.visitors import visitors as visitor_service

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/accommodations", response_model=AccommodationMarket)
def accommodations(
    db: Database, org: OrganizationContext, property_id: UUID, reference_date: date | None = None
) -> AccommodationMarket:
    return service.accommodations(db, org, property_id, reference_date)


@router.get("/visitors", response_model=VisitorMarket)
def visitors(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    category: Literal["1", "2", "3"] = "2",
    days: Annotated[int, Query(ge=1, le=120)] = 90,
) -> VisitorMarket:
    return visitor_service(db, org, property_id, category, days)
