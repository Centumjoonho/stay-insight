from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VisitorDaily(Base):
    __tablename__ = "tourism_visitor_daily"
    __table_args__ = (
        UniqueConstraint("source", "source_region_code", "visitor_category_code", "reference_date"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    region_id: Mapped[UUID] = mapped_column(ForeignKey("app.regions.id"))
    source: Mapped[str] = mapped_column(String(40))
    source_dataset: Mapped[str] = mapped_column(String(100))
    source_region_code: Mapped[str] = mapped_column(String(5))
    source_region_name: Mapped[str] = mapped_column(String(40))
    visitor_category_code: Mapped[str] = mapped_column(String(1))
    visitor_category_name: Mapped[str] = mapped_column(String(40))
    reference_date: Mapped[date]
    visitor_value: Mapped[Decimal | None] = mapped_column(Numeric())
    day_of_week_code: Mapped[str | None] = mapped_column(String(1))
    day_of_week_name: Mapped[str | None] = mapped_column(String(10))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
