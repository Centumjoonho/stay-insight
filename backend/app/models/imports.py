from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Channel(StrEnum):
    AIRBNB = "AIRBNB"
    BOOKING = "BOOKING"
    AGODA = "AGODA"
    DIRECT = "DIRECT"
    GENERIC = "GENERIC"


class ReservationStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


CHANNEL_CHECK = "channel IN ('AIRBNB','BOOKING','AGODA','DIRECT','GENERIC')"


class ReservationImport(Base):
    __tablename__ = "reservation_imports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["app.properties.organization_id", "app.properties.id"],
        ),
        UniqueConstraint("organization_id", "property_id", "id"),
        CheckConstraint(CHANNEL_CHECK),
        CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')"),
        CheckConstraint("total_rows >= 0 AND imported_rows >= 0 AND rejected_rows >= 0"),
        CheckConstraint("imported_rows <= total_rows AND rejected_rows <= total_rows"),
        Index("ix_imports_scope", "organization_id", "property_id", "created_at"),
        Index(
            "uq_imports_completed_file",
            "property_id",
            "channel",
            "file_checksum",
            unique=True,
            postgresql_where=text("status = 'COMPLETED'"),
        ),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    property_id: Mapped[UUID]
    channel: Mapped[str] = mapped_column(String(20))
    original_filename: Mapped[str] = mapped_column(String(200))
    file_checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    total_rows: Mapped[int]
    imported_rows: Mapped[int] = mapped_column(default=0)
    rejected_rows: Mapped[int] = mapped_column(default=0)
    inserted_rows: Mapped[int] = mapped_column(default=0)
    updated_rows: Mapped[int] = mapped_column(default=0)
    created_by_user_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(300))
    column_mapping: Mapped[dict[str, str]] = mapped_column(JSONB)
    validation_errors: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    adapter_version: Mapped[str] = mapped_column(String(30), default="generic-v1")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["app.properties.organization_id", "app.properties.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "property_id", "import_id"],
            [
                "app.reservation_imports.organization_id",
                "app.reservation_imports.property_id",
                "app.reservation_imports.id",
            ],
        ),
        UniqueConstraint("property_id", "channel", "external_reservation_id"),
        CheckConstraint(CHANNEL_CHECK),
        CheckConstraint("check_out > check_in AND booked_nights = check_out - check_in"),
        CheckConstraint("guest_count IS NULL OR guest_count >= 1"),
        CheckConstraint("gross_revenue >= 0 AND gross_revenue <> 'NaN'::numeric"),
        CheckConstraint(
            "channel_fee IS NULL OR (channel_fee >= 0 AND channel_fee <= gross_revenue)"
        ),
        CheckConstraint(
            "(channel_fee IS NULL AND net_revenue IS NULL) OR "
            "(channel_fee IS NOT NULL AND net_revenue IS NOT NULL "
            "AND net_revenue = gross_revenue - channel_fee)"
        ),
        CheckConstraint("reservation_status IN ('CONFIRMED','CANCELLED','UNKNOWN')"),
        Index("ix_reservations_scope_date", "organization_id", "property_id", "check_in", "id"),
        Index("ix_reservations_import", "organization_id", "property_id", "import_id"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    property_id: Mapped[UUID]
    import_id: Mapped[UUID]
    channel: Mapped[str] = mapped_column(String(20))
    external_reservation_id: Mapped[str] = mapped_column(String(200))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    booked_nights: Mapped[int]
    guest_count: Mapped[int | None]
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 0))
    channel_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 0))
    net_revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 0))
    reservation_status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
