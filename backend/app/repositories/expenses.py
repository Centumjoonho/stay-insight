from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.expenses import CostType, Expense, ExpenseCategory
from app.models.imports import Reservation


def get(db: Session, org: UUID, expense_id: UUID) -> Expense | None:
    return db.scalar(
        select(Expense).where(Expense.organization_id == org, Expense.id == expense_id)
    )


def insert(db: Session, item: Expense) -> Expense:
    db.add(item)
    db.flush()
    return item


def save(db: Session, org: UUID, expense_id: UUID, changes: dict[str, object]) -> Expense | None:
    return db.scalar(
        update(Expense)
        .where(Expense.organization_id == org, Expense.id == expense_id)
        .values(**changes)
        .returning(Expense)
        .execution_options(populate_existing=True)
    )


def remove(db: Session, org: UUID, expense_id: UUID) -> UUID | None:
    return db.scalar(
        delete(Expense)
        .where(Expense.organization_id == org, Expense.id == expense_id)
        .returning(Expense.id)
    )


def list_expenses(
    db: Session,
    org: UUID,
    property_id: UUID,
    start: date | None,
    end: date | None,
    category: ExpenseCategory | None,
    cost_type: CostType | None,
    limit: int,
    offset: int,
) -> tuple[list[Expense], int]:
    scope = [Expense.organization_id == org, Expense.property_id == property_id]
    if start:
        scope.append(Expense.expense_date >= start)
    if end:
        scope.append(Expense.expense_date <= end)
    if category:
        scope.append(Expense.category == category)
    if cost_type:
        scope.append(Expense.cost_type == cost_type)
    items = list(
        db.scalars(
            select(Expense)
            .where(*scope)
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc(), Expense.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(Expense).where(*scope)) or 0
    return items, total


def cost_groups(
    db: Session, org: UUID, property_id: UUID, start: date, end: date
) -> list[tuple[str, str, Decimal]]:
    rows = db.execute(
        select(Expense.category, Expense.cost_type, func.sum(Expense.amount))
        .where(
            Expense.organization_id == org,
            Expense.property_id == property_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Expense.category, Expense.cost_type)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows]


def channel_fees(
    db: Session, org: UUID, property_id: UUID, start: date, end: date
) -> tuple[Decimal, int, int]:
    row = db.execute(
        select(
            func.coalesce(func.sum(Reservation.channel_fee), 0),
            func.count(Reservation.channel_fee),
            func.count(),
        ).where(
            Reservation.organization_id == org,
            Reservation.property_id == property_id,
            Reservation.check_in >= start,
            Reservation.check_in <= end,
        )
    ).one()
    return Decimal(row[0]), row[1], row[2] - row[1]
