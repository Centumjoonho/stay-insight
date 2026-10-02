from datetime import date
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.events import TourismEvent
from app.models.market import PublicDataSyncRun, Region
from app.providers.events import REGIONS, SOURCE, EventError

LOCK_KEY = "public-events:" + SOURCE


def lock_sync(db: Session) -> None:
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key,0))"), {"key": LOCK_KEY}
    ):
        raise EventError("EVENT_ALREADY_RUNNING")


def regions(db: Session) -> dict[str, UUID]:
    rows = list(
        db.scalars(
            select(Region).where(Region.sido_name == "부산광역시", Region.region_level == "SIGUNGU")
        )
    )
    names = {r.sigungu_name: r.id for r in rows}
    if len(rows) != 16 or len(names) != 16 or set(names) != set(REGIONS.values()):
        raise EventError("EVENT_REGION_MAPPING_INVALID")
    return {code: names[name] for code, name in REGIONS.items()}


def existing(db: Session) -> dict[str, TourismEvent]:
    return {
        row.source_event_id: row
        for row in db.scalars(select(TourismEvent).where(TourismEvent.source == SOURCE))
    }


def latest_run(db: Session, completed: bool = False) -> PublicDataSyncRun | None:
    query = select(PublicDataSyncRun).where(PublicDataSyncRun.source == SOURCE)
    if completed:
        query = query.where(PublicDataSyncRun.status == "COMPLETED")
    return db.scalar(query.order_by(PublicDataSyncRun.started_at.desc()).limit(1))


def matches(region: UUID, start: date, end: date) -> tuple[ColumnElement[bool], ...]:
    return (
        TourismEvent.source == SOURCE,
        TourismEvent.region_id == region,
        TourismEvent.start_date <= end,
        TourismEvent.end_date >= start,
    )


def read(
    db: Session, region: UUID, start: date, end: date, today: date, limit: int
) -> tuple[list[TourismEvent], int]:
    filters = matches(region, start, end)
    total = db.scalar(select(func.count()).select_from(TourismEvent).where(*filters)) or 0
    ongoing = (TourismEvent.start_date <= today) & (TourismEvent.end_date >= today)
    rows = list(
        db.scalars(
            select(TourismEvent)
            .where(*filters)
            .order_by(
                case((ongoing, 0), else_=1), TourismEvent.start_date, TourismEvent.source_event_id
            )
            .limit(limit)
        )
    )
    return rows, total


def counts(db: Session, region: UUID, today: date, future: date) -> tuple[int, int]:
    base = (TourismEvent.source == SOURCE, TourismEvent.region_id == region)
    ongoing = (
        db.scalar(
            select(func.count())
            .select_from(TourismEvent)
            .where(*base, TourismEvent.start_date <= today, TourismEvent.end_date >= today)
        )
        or 0
    )
    upcoming = (
        db.scalar(
            select(func.count())
            .select_from(TourismEvent)
            .where(*base, TourismEvent.start_date > today, TourismEvent.start_date <= future)
        )
        or 0
    )
    return ongoing, upcoming
