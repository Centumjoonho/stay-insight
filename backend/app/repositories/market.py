from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.market import PublicAccommodationLicense as License
from app.models.market import PublicDataSyncRun, Region
from app.providers.accommodation import SOURCE, LicenseRecord
from app.repositories.regions import supported_region


def regions(db: Session) -> dict[str, Region]:
    return {r.sigungu_name: r for r in db.scalars(select(Region))}


def latest_run(
    db: Session, completed: bool = False, district: str | None = None
) -> PublicDataSyncRun | None:
    query = select(PublicDataSyncRun).where(PublicDataSyncRun.source == SOURCE)
    if completed:
        query = query.where(PublicDataSyncRun.status == "COMPLETED")
    if district:
        query = query.where(PublicDataSyncRun.covered_districts.contains([district]))
    order = PublicDataSyncRun.completed_at if completed else PublicDataSyncRun.started_at
    return db.scalar(query.order_by(order.desc()).limit(1))


def lock_sync(db: Session) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": "public-license:" + SOURCE},
    )


def existing(db: Session) -> dict[str, License]:
    return {
        r.source_record_id: r for r in db.scalars(select(License).where(License.source == SOURCE))
    }


def record_values(record: LicenseRecord, region_id: UUID) -> dict[str, object]:
    values = record.model_dump(exclude={"sigungu_name"})
    return {**values, "region_id": region_id, "source": SOURCE}


def counts(db: Session, region_id: UUID, start: date, end: date) -> dict[str, int]:
    scope = (License.source == SOURCE, License.region_id == region_id)
    row = db.execute(
        select(
            func.count().label("total"),
            func.count().filter(License.normalized_business_status == "OPEN").label("open"),
            func.count().filter(License.license_date.between(start, end)).label("new"),
            func.count()
            .filter(
                License.normalized_business_status == "CLOSED",
                License.closure_date.between(start, end),
            )
            .label("closed"),
            func.count().filter(License.license_date.is_(None)).label("missing_license_dates"),
            func.count()
            .filter(License.normalized_business_status == "CLOSED", License.closure_date.is_(None))
            .label("missing_closure_dates"),
            func.count().filter(License.normalized_business_status == "UNKNOWN").label("unknown"),
        ).where(*scope)
    ).one()
    return {key: int(value) for key, value in row._mapping.items()}


def type_counts(db: Session, region_id: UUID) -> dict[str, int]:
    return {
        str(kind): int(count)
        for kind, count in db.execute(
            select(License.normalized_license_type, func.count())
            .where(
                License.source == SOURCE,
                License.region_id == region_id,
                License.normalized_business_status == "OPEN",
            )
            .group_by(License.normalized_license_type)
            .order_by(License.normalized_license_type)
        )
    }


def property_region(db: Session, org: UUID, property_id: UUID) -> Region | None:
    region_id = db.scalar(
        text("""SELECT region_id FROM app.properties
        WHERE id=:id AND organization_id=:org"""),
        {"id": property_id, "org": org},
    )
    return supported_region(db, region_id) if region_id else None


def assign_property_region(
    db: Session,
    org: UUID,
    property_id: UUID,
    region_id: UUID,
    address: str,
) -> bool:
    changed = db.scalar(
        text("""UPDATE app.properties
        SET region_id=:region, updated_at=now()
        WHERE id=:id AND organization_id=:org AND address=:address RETURNING id"""),
        {"region": region_id, "id": property_id, "org": org, "address": address},
    )
    return changed is not None
