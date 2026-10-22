from dataclasses import asdict
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.importers.generic import NormalizedRow
from app.models.imports import Reservation, ReservationImport


def lock_import(db: Session, org: UUID, property_id: UUID, channel: str) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"import:{org}:{property_id}:{channel}"},
    )


def duplicate(
    db: Session, org: UUID, property_id: UUID, channel: str, checksum: str
) -> ReservationImport | None:
    return db.scalar(
        select(ReservationImport).where(
            ReservationImport.organization_id == org,
            ReservationImport.property_id == property_id,
            ReservationImport.channel == channel,
            ReservationImport.file_checksum == checksum,
            ReservationImport.status == "COMPLETED",
        )
    )


def save_batch(db: Session, batch: ReservationImport) -> None:
    db.add(batch)
    db.flush()


def upsert_rows(
    db: Session, batch: ReservationImport, rows: list[NormalizedRow]
) -> tuple[int, int]:
    from fastapi import HTTPException

    from app.repositories import reservations as manual
    from app.schemas.reservations import ReservationValues
    from app.services.reservations import apply

    # Same channel advisory lock as manual creation; rows ordered for deterministic locking.
    existing = {
        r.external_reservation_id: r
        for r in db.scalars(
            select(Reservation)
            .where(
                Reservation.organization_id == batch.organization_id,
                Reservation.property_id == batch.property_id,
                Reservation.channel == batch.channel,
                Reservation.external_reservation_id.in_([r.external_reservation_id for r in rows]),
            )
            .order_by(Reservation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }
    protected = manual.protections(db, batch.organization_id, [r.id for r in existing.values()])
    inserted = updated = preserved = 0
    for row in rows:
        item = existing.get(row.external_reservation_id)
        if item is not None and item.origin != "CSV_IMPORT":
            raise HTTPException(409, "CSV_MANUAL_IDENTITY_CONFLICT")
        raw = asdict(row)
        if item is None:
            item = Reservation(
                **raw,
                organization_id=batch.organization_id,
                property_id=batch.property_id,
                channel=batch.channel,
                import_id=batch.id,
                origin="CSV_IMPORT",
                version=1,
            )
            db.add(item)
            inserted += 1
        else:
            before = manual.snapshot(item)
            fields = protected.get(item.id, [])
            preserved += len(fields)
            merged = {f: (getattr(item, f) if f in fields else raw[f]) for f in before}
            # Individually valid CSV and manual values can form an invalid combined row.
            # Reject the WHOLE batch in the existing savepoint, never partially publish.
            values = ReservationValues.model_validate(merged)
            changes = [f for f in before if getattr(item, f) != getattr(values, f)]
            if changes:
                apply(item, values)
                item.version += 1
                manual.audit(
                    db,
                    item,
                    batch.created_by_user_id,
                    "CSV_UPDATE",
                    "CSV_IMPORT",
                    {f: before[f] for f in changes},
                    {f: manual.snapshot(item)[f] for f in changes},
                    changes,
                    import_id=batch.id,
                )
                item.import_id = batch.id
            updated += 1
    db.flush()
    update_batch(
        db,
        batch.organization_id,
        batch.property_id,
        batch.id,
        {"protected_fields_count": preserved},
    )
    return inserted, updated


def get_import(db: Session, org: UUID, item_id: UUID) -> ReservationImport | None:
    return db.scalar(
        select(ReservationImport).where(
            ReservationImport.organization_id == org, ReservationImport.id == item_id
        )
    )


def list_imports(
    db: Session, org: UUID, property_id: UUID | None, channel: str | None, limit: int, offset: int
) -> tuple[list[ReservationImport], int]:
    conditions = [ReservationImport.organization_id == org]
    if property_id:
        conditions.append(ReservationImport.property_id == property_id)
    if channel:
        conditions.append(ReservationImport.channel == channel)
    items = list(
        db.scalars(
            select(ReservationImport)
            .where(*conditions)
            .order_by(ReservationImport.created_at.desc(), ReservationImport.id)
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(ReservationImport).where(*conditions))
    return items, total or 0


def get_reservation(db: Session, org: UUID, item_id: UUID) -> Reservation | None:
    return db.scalar(
        select(Reservation).where(Reservation.organization_id == org, Reservation.id == item_id)
    )


def list_reservations(
    db: Session,
    org: UUID,
    property_id: UUID | None,
    channel: str | None,
    from_date: date | None,
    to_date: date | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Reservation], int]:
    conditions = [Reservation.organization_id == org]
    for column, value in (
        (Reservation.property_id, property_id),
        (Reservation.channel, channel),
        (Reservation.reservation_status, status),
    ):
        if value is not None:
            conditions.append(column == value)
    if from_date:
        conditions.append(Reservation.check_in >= from_date)
    if to_date:
        conditions.append(Reservation.check_in <= to_date)
    items = list(
        db.scalars(
            select(Reservation)
            .where(*conditions)
            .order_by(Reservation.check_in.desc(), Reservation.id)
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(Reservation).where(*conditions))
    return items, total or 0


def update_batch(
    db: Session, org: UUID, property_id: UUID, batch_id: UUID, changes: dict[str, object]
) -> ReservationImport:
    item = db.scalar(
        update(ReservationImport)
        .where(
            ReservationImport.organization_id == org,
            ReservationImport.property_id == property_id,
            ReservationImport.id == batch_id,
        )
        .values(**changes)
        .returning(ReservationImport)
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise RuntimeError("Import batch is no longer accessible")
    return item
