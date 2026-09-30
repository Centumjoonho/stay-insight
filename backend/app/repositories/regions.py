from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market import Region
from app.providers.accommodation import BUSAN_DISTRICTS


def supported_regions(db: Session) -> list[Region]:
    return list(
        db.scalars(
            select(Region)
            .where(
                Region.sido_name == "부산광역시",
                Region.region_level == "SIGUNGU",
                Region.sigungu_name.in_(BUSAN_DISTRICTS),
            )
            .order_by(Region.sigungu_name, Region.id)
        )
    )


def supported_region(db: Session, region_id: UUID) -> Region | None:
    return db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.sido_name == "부산광역시",
            Region.region_level == "SIGUNGU",
            Region.sigungu_name.in_(BUSAN_DISTRICTS),
        )
    )
