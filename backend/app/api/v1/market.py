from datetime import date
from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies.tenant import Database, OrganizationContext
from app.schemas.market import AccommodationMarket
from app.services import market as service

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/accommodations", response_model=AccommodationMarket)
def accommodations(
    db: Database, org: OrganizationContext, property_id: UUID, reference_date: date | None = None
) -> AccommodationMarket:
    return service.accommodations(db, org, property_id, reference_date)
