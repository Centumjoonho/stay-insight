from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.market import Region
from app.repositories import market as market_repo
from app.repositories import regions as repo
from app.schemas.regions import RegionResponse


def list_regions(db: Session, sido: str, level: str) -> list[RegionResponse]:
    if sido != "부산광역시" or level != "SIGUNGU":
        raise HTTPException(422, "Only supported Busan sigungu regions are available")
    return [RegionResponse.model_validate(item) for item in repo.supported_regions(db)]


def validate_region(db: Session, region_id: UUID | None) -> Region | None:
    if region_id is None:
        return None
    item = repo.supported_region(db, region_id)
    if item is None:
        raise HTTPException(422, "Select a supported Busan sigungu region")
    return item


def assign_property_region(
    db: Session,
    org: UUID,
    property_id: UUID,
    district: str,
    address: str,
) -> bool:
    # Maintenance command shares the same supported-region lookup as HTTP writes.
    region = next((r for r in repo.supported_regions(db) if r.sigungu_name == district), None)
    if region is None:
        return False
    validate_region(db, region.id)
    return market_repo.assign_property_region(db, org, property_id, region.id, address)
