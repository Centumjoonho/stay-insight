from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.imports import Reservation
from app.models.reservations import ReservationAudit, ReservationOverride
from app.reservation_fields import MUTABLE_FIELDS


def locked(db: Session, org: UUID, item_id: UUID) -> Reservation | None:
    return db.scalar(
        select(Reservation)
        .where(Reservation.organization_id == org, Reservation.id == item_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def protections(db: Session, org: UUID, ids: list[UUID]) -> dict[UUID, list[str]]:
    result: dict[UUID, list[str]] = {}
    for rid, field in db.execute(
        select(ReservationOverride.reservation_id, ReservationOverride.field_name).where(
            ReservationOverride.organization_id == org, ReservationOverride.reservation_id.in_(ids)
        )
    ):
        result.setdefault(rid, []).append(field)
    return {key: sorted(value) for key, value in result.items()}


def protect(db: Session, item: Reservation, fields: list[str], actor: UUID) -> None:
    existing = protections(db, item.organization_id, [item.id]).get(item.id, [])
    for field in fields:
        if field not in existing:
            db.add(
                ReservationOverride(
                    organization_id=item.organization_id,
                    property_id=item.property_id,
                    reservation_id=item.id,
                    field_name=field,
                    created_by_subject=actor,
                )
            )


def release(db: Session, org: UUID, item_id: UUID, fields: list[str]) -> None:
    db.execute(
        delete(ReservationOverride).where(
            ReservationOverride.organization_id == org,
            ReservationOverride.reservation_id == item_id,
            ReservationOverride.field_name.in_(fields),
        )
    )


def snapshot(item: Reservation) -> dict[str, object]:
    def value(raw: object) -> object:
        if isinstance(raw, date):
            return raw.isoformat()
        if isinstance(raw, Decimal):
            return format(raw, "f")
        return raw

    return {field: value(getattr(item, field)) for field in MUTABLE_FIELDS}


def audit(
    db: Session,
    item: Reservation,
    actor: UUID,
    kind: str,
    source: str,
    before: dict[str, object],
    after: dict[str, object],
    fields: list[str],
    reason: str | None = None,
    import_id: UUID | None = None,
) -> None:
    db.add(
        ReservationAudit(
            organization_id=item.organization_id,
            property_id=item.property_id,
            reservation_id=item.id,
            event_type=kind,
            change_source=source,
            actor_subject=actor,
            reservation_import_id=import_id,
            reason=reason,
            changed_fields=fields,
            before_values=before,
            after_values=after,
        )
    )


def history(
    db: Session, org: UUID, item_id: UUID, limit: int, offset: int
) -> tuple[list[ReservationAudit], int]:
    conditions = (
        ReservationAudit.organization_id == org,
        ReservationAudit.reservation_id == item_id,
    )
    rows = list(
        db.scalars(
            select(ReservationAudit)
            .where(*conditions)
            .order_by(ReservationAudit.created_at.desc(), ReservationAudit.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(ReservationAudit).where(*conditions)) or 0
    return rows, total
