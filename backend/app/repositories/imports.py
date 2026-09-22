from dataclasses import asdict
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
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
    existing = set(
        db.scalars(
            select(Reservation.external_reservation_id).where(
                Reservation.organization_id == batch.organization_id,
                Reservation.property_id == batch.property_id,
                Reservation.channel == batch.channel,
                Reservation.external_reservation_id.in_([r.external_reservation_id for r in rows]),
            )
        )
    )
    updated = sum(row.external_reservation_id in existing for row in rows)
    # Bounded chunks stay below PostgreSQL's bind-parameter limit.
    for start in range(0, len(rows), 250):
        statement = insert(Reservation).values(
            [
                {
                    **asdict(row),
                    "organization_id": batch.organization_id,
                    "property_id": batch.property_id,
                    "channel": batch.channel,
                    "import_id": batch.id,
                }
                for row in rows[start : start + 250]
            ]
        )
        fields = (
            "import_id",
            "check_in",
            "check_out",
            "booked_nights",
            "guest_count",
            "gross_revenue",
            "channel_fee",
            "net_revenue",
            "reservation_status",
        )
        statement = statement.on_conflict_do_update(
            index_elements=["property_id", "channel", "external_reservation_id"],
            set_={
                **{field: getattr(statement.excluded, field) for field in fields},
                "updated_at": func.now(),
            },
            where=(Reservation.organization_id == batch.organization_id)
            & (Reservation.property_id == batch.property_id),
        )
        db.execute(statement)
    return len(rows) - updated, updated


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
