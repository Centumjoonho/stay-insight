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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExpenseCategory(StrEnum):
    RENT = "RENT"
    MANAGEMENT_FEE = "MANAGEMENT_FEE"
    CLEANING = "CLEANING"
    LAUNDRY = "LAUNDRY"
    ELECTRICITY = "ELECTRICITY"
    GAS = "GAS"
    WATER = "WATER"
    SUPPLIES = "SUPPLIES"
    LABOR = "LABOR"
    MARKETING = "MARKETING"
    MAINTENANCE = "MAINTENANCE"
    SUBSCRIPTION = "SUBSCRIPTION"
    INSURANCE = "INSURANCE"
    TAX_AND_FEE = "TAX_AND_FEE"
    OTHER = "OTHER"


class CostType(StrEnum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["app.properties.organization_id", "app.properties.id"],
        ),
        CheckConstraint("amount >= 0 AND amount <> 'NaN'::numeric"),
        CheckConstraint(
            "category IN (" + ",".join("'" + c.value + "'" for c in ExpenseCategory) + ")"
        ),
        CheckConstraint("cost_type IN ('FIXED','VARIABLE')"),
        CheckConstraint("source = 'MANUAL'"),
        Index("ix_expenses_scope_date", "organization_id", "property_id", "expense_date", "id"),
        {"schema": "app"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("app.organizations.id"))
    property_id: Mapped[UUID]
    expense_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(30))
    cost_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0))
    memo: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(20), default="MANUAL")
    created_by_user_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
