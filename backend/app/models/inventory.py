from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CapacityPeriod(Base):
    __tablename__ = "property_capacity_periods"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["app.properties.organization_id", "app.properties.id"],
        ),
        CheckConstraint("inventory_units > 0"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from"),
        ExcludeConstraint(
            ("property_id", "="),
            (text("daterange(effective_from,effective_to,'[]')"), "&&"),
            name="capacity_no_overlap",
            using="gist",
        ),
        Index("ix_capacity_scope_date", "organization_id", "property_id", "effective_from"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    property_id: Mapped[UUID]
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    inventory_units: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AvailabilityOverride(Base):
    __tablename__ = "property_availability_overrides"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["app.properties.organization_id", "app.properties.id"],
        ),
        UniqueConstraint("organization_id", "property_id", "date"),
        CheckConstraint("unavailable_units >= 0"),
        CheckConstraint("reason IN ('MAINTENANCE','OWNER_BLOCK','SALES_STOP','OTHER')"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    property_id: Mapped[UUID]
    date: Mapped[date]
    unavailable_units: Mapped[int]
    reason: Mapped[str] = mapped_column(String(20))
    memo: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
