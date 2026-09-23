from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.expenses import CostType, Expense, ExpenseCategory
from app.repositories import expenses as repo
from app.schemas.expenses import (
    CategoryTotal,
    CostTypeTotal,
    ExpenseCreate,
    ExpenseList,
    ExpensePatch,
    ExpenseResponse,
    ExpenseSummary,
)
from app.services.foundation import get_property


def validate_period(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise HTTPException(422, "from must be on or before to")


def create(db: Session, org: UUID, user: UUID, body: ExpenseCreate) -> Expense:
    get_property(db, org, body.property_id)
    return repo.insert(
        db,
        Expense(organization_id=org, created_by_user_id=user, source="MANUAL", **body.model_dump()),
    )


def get(db: Session, org: UUID, expense_id: UUID) -> Expense:
    item = repo.get(db, org, expense_id)
    if item is None:
        raise HTTPException(404, "Expense not found")
    get_property(db, org, item.property_id)
    return item


def update(db: Session, org: UUID, expense_id: UUID, body: ExpensePatch) -> Expense:
    get(db, org, expense_id)
    item = repo.save(db, org, expense_id, body.model_dump(exclude_unset=True))
    if item is None:
        raise HTTPException(404, "Expense not found")
    return item


def delete(db: Session, org: UUID, expense_id: UUID) -> None:
    get(db, org, expense_id)
    if repo.remove(db, org, expense_id) is None:
        raise HTTPException(404, "Expense not found")


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
) -> ExpenseList:
    get_property(db, org, property_id)
    validate_period(start, end)
    items, total = repo.list_expenses(
        db, org, property_id, start, end, category, cost_type, limit, offset
    )
    return ExpenseList(items=[ExpenseResponse.model_validate(item) for item in items], total=total)


def summary(db: Session, org: UUID, property_id: UUID, start: date, end: date) -> ExpenseSummary:
    get_property(db, org, property_id)
    validate_period(start, end)
    categories: dict[str, Decimal] = {}
    types = {kind.value: Decimal(0) for kind in CostType}
    for category, kind, amount in repo.cost_groups(db, org, property_id, start, end):
        categories[category] = categories.get(category, Decimal(0)) + amount
        types[kind] += amount
    manual = sum(types.values(), Decimal(0))
    fee, present, missing = repo.channel_fees(db, org, property_id, start, end)
    return ExpenseSummary(
        property_id=property_id,
        from_date=start,
        to_date=end,
        manual_expense_total=manual,
        fixed_expense_total=types["FIXED"],
        variable_expense_total=types["VARIABLE"],
        channel_fee_total=fee,
        known_cost_total=manual + fee,
        category_breakdown=[
            CategoryTotal(category=ExpenseCategory(key), amount=value)
            for key, value in sorted(categories.items())
        ],
        cost_type_breakdown=[
            CostTypeTotal(cost_type=CostType(key), amount=value) for key, value in types.items()
        ],
        reservations_with_fee=present,
        reservations_missing_fee=missing,
    )
