from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.market import PublicDataSyncRun, Region
from app.models.visitors import VisitorDaily
from app.providers.visitor_api import REGIONS, SOURCE, VisitorError

LOCK_KEY = "public-visitors:" + SOURCE


def lock_sync(db: Session) -> None:
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key,0))"), {"key": LOCK_KEY}
    ):
        raise VisitorError("VISITOR_ALREADY_RUNNING")


def resolve_regions(db: Session) -> dict[str, UUID]:
    rows = list(
        db.scalars(
            select(Region).where(Region.sido_name == "부산광역시", Region.region_level == "SIGUNGU")
        )
    )
    by_name = {row.sigungu_name: row.id for row in rows}
    if len(rows) != 16 or len(by_name) != 16 or set(by_name) != set(REGIONS.values()):
        raise VisitorError("VISITOR_REGION_MAPPING_INVALID")
    return {code: by_name[name] for code, name in REGIONS.items()}


def existing(db: Session, start: date, end: date) -> list[VisitorDaily]:
    return list(
        db.scalars(
            select(VisitorDaily).where(
                VisitorDaily.source == SOURCE, VisitorDaily.reference_date.between(start, end)
            )
        )
    )


def latest_day(db: Session, region: UUID, category: str) -> date | None:
    return db.scalar(
        select(func.max(VisitorDaily.reference_date)).where(
            VisitorDaily.source == SOURCE,
            VisitorDaily.region_id == region,
            VisitorDaily.visitor_category_code == category,
            VisitorDaily.visitor_value.is_not(None),
        )
    )


def observations(
    db: Session, region: UUID, category: str, start: date, end: date
) -> list[VisitorDaily]:
    return list(
        db.scalars(
            select(VisitorDaily).where(
                VisitorDaily.source == SOURCE,
                VisitorDaily.region_id == region,
                VisitorDaily.visitor_category_code == category,
                VisitorDaily.reference_date.between(start, end),
            )
        )
    )


def latest_run(db: Session, completed: bool = False) -> PublicDataSyncRun | None:
    query = select(PublicDataSyncRun).where(PublicDataSyncRun.source == SOURCE)
    if completed:
        query = query.where(PublicDataSyncRun.status == "COMPLETED")
    return db.scalar(query.order_by(PublicDataSyncRun.started_at.desc()).limit(1))
