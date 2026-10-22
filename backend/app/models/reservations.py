from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKeyConstraint, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReservationOverride(Base):
    __tablename__ = "reservation_manual_overrides"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id", "reservation_id"],
            [
                "app.reservations.organization_id",
                "app.reservations.property_id",
                "app.reservations.id",
            ],
        ),
        UniqueConstraint("reservation_id", "field_name"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    property_id: Mapped[UUID]
    reservation_id: Mapped[UUID]
    field_name: Mapped[str] = mapped_column(String(30))
    created_by_subject: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReservationAudit(Base):
    __tablename__ = "reservation_audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id", "reservation_id"],
            [
                "app.reservations.organization_id",
                "app.reservations.property_id",
                "app.reservations.id",
            ],
        ),
        ForeignKeyConstraint(
            ["organization_id", "property_id", "reservation_import_id"],
            [
                "app.reservation_imports.organization_id",
                "app.reservation_imports.property_id",
                "app.reservation_imports.id",
            ],
        ),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    property_id: Mapped[UUID]
    reservation_id: Mapped[UUID]
    event_type: Mapped[str] = mapped_column(String(30))
    change_source: Mapped[str] = mapped_column(String(20))
    actor_subject: Mapped[UUID]
    reservation_import_id: Mapped[UUID | None]
    reason: Mapped[str | None] = mapped_column(String(500))
    changed_fields: Mapped[list[str]] = mapped_column(JSONB)
    before_values: Mapped[dict[str, object]] = mapped_column(JSONB)
    after_values: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
