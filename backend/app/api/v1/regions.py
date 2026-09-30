from fastapi import APIRouter, Query

from app.api.dependencies.tenant import Database
from app.schemas.regions import RegionResponse
from app.services import regions as service

router = APIRouter()


@router.get("/regions", response_model=list[RegionResponse])
def regions(
    db: Database,
    sido: str = Query("부산광역시", max_length=40),
    level: str = Query("SIGUNGU", max_length=20),
) -> list[RegionResponse]:
    # Database dependency requires verified JWT; shared reference data needs no tenant selector.
    return service.list_regions(db, sido, level)
