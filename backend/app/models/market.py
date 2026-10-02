from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Region(Base):
    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("sido_name", "sigungu_name"), {"schema": "app"})
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sido_name: Mapped[str] = mapped_column(String(40), default="부산광역시")
    sigungu_name: Mapped[str] = mapped_column(String(40))
    region_level: Mapped[str] = mapped_column(String(20), default="SIGUNGU")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicAccommodationLicense(Base):
    __tablename__ = "public_accommodation_licenses"
    __table_args__ = (UniqueConstraint("source", "source_record_id"), {"schema": "app"})
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(40))
    source_record_id: Mapped[str] = mapped_column(String(200))
    business_name: Mapped[str] = mapped_column(String(300))
    source_license_type: Mapped[str] = mapped_column(String(200))
    normalized_license_type: Mapped[str] = mapped_column(String(40))
    source_business_status: Mapped[str] = mapped_column(String(200))
    normalized_business_status: Mapped[str] = mapped_column(String(20))
    region_id: Mapped[UUID] = mapped_column(ForeignKey("app.regions.id"))
    license_date: Mapped[date | None]
    closure_date: Mapped[date | None]
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicDataSyncRun(Base):
    __tablename__ = "public_data_sync_runs"
    __table_args__ = {"schema": "app"}
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_reference_date: Mapped[date | None]
    closure_dates_supported: Mapped[bool] = mapped_column(default=False)
    covered_districts: Mapped[list[str]] = mapped_column(JSONB, default=list)
    fetched_count: Mapped[int] = mapped_column(default=0)
    inserted_count: Mapped[int] = mapped_column(default=0)
    updated_count: Mapped[int] = mapped_column(default=0)
    unchanged_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    visitor_coverage: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    event_coverage: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error_summary: Mapped[str | None] = mapped_column(String(100))
