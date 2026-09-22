from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(StrEnum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class AccommodationType(StrEnum):
    HOTEL = "HOTEL"
    MOTEL = "MOTEL"
    HOSTEL = "HOSTEL"
    GUESTHOUSE = "GUESTHOUSE"
    LIFESTYLE_ACCOMMODATION = "LIFESTYLE_ACCOMMODATION"
    PENSION = "PENSION"
    VACATION_RENTAL = "VACATION_RENTAL"
    OTHER = "OTHER"


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0"), {"schema": "app"})

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint("role IN ('OWNER', 'MEMBER')"),
        Index("ix_organization_members_user_id", "user_id"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    user_id: Mapped[UUID]
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("inventory_units >= 1"),
        CheckConstraint("length(trim(name)) > 0 AND length(trim(address)) > 0"),
        CheckConstraint("latitude BETWEEN -90 AND 90"),
        CheckConstraint("longitude BETWEEN -180 AND 180"),
        CheckConstraint("(latitude IS NULL) = (longitude IS NULL)"),
        CheckConstraint("timezone = 'Asia/Seoul'"),
        CheckConstraint(
            "accommodation_type IN ("
            + ", ".join("'" + item.value + "'" for item in AccommodationType)
            + ")"
        ),
        Index("ix_properties_organization_id", "organization_id"),
        {"schema": "app"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(500))
    road_address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    accommodation_type: Mapped[str] = mapped_column(String(40))
    inventory_units: Mapped[int]
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Seoul", server_default="Asia/Seoul"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
