from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TourismEvent(Base):
    __tablename__ = "tourism_events"
    __table_args__ = (UniqueConstraint("source", "source_event_id"), {"schema": "app"})
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(40))
    source_dataset: Mapped[str] = mapped_column(String(100))
    source_event_id: Mapped[str] = mapped_column(String(40))
    region_id: Mapped[UUID] = mapped_column(ForeignKey("app.regions.id"))
    source_region_code: Mapped[str] = mapped_column(String(2))
    source_sigungu_code: Mapped[str] = mapped_column(String(3))
    title: Mapped[str] = mapped_column(String(500))
    start_date: Mapped[date]
    end_date: Mapped[date]
    address: Mapped[str | None] = mapped_column(String(1001))
    source_status: Mapped[str | None] = mapped_column(String(100))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
