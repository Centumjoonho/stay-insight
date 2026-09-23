from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.dependencies.tenant import CurrentUser, Database, OrganizationContext
from app.models.expenses import CostType, Expense, ExpenseCategory
from app.schemas.expenses import (
    ExpenseCreate,
    ExpenseList,
    ExpensePatch,
    ExpenseResponse,
    ExpenseSummary,
)
from app.services import expenses as service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseResponse, status_code=201)
def create(
    body: ExpenseCreate, db: Database, org: OrganizationContext, user: CurrentUser
) -> Expense:
    return service.create(db, org, user.user_id, body)


@router.get("", response_model=ExpenseList)
def list_expenses(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    category: ExpenseCategory | None = None,
    cost_type: CostType | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ExpenseList:
    return service.list_expenses(
        db, org, property_id, from_date, to_date, category, cost_type, limit, offset
    )


@router.get("/summary", response_model=ExpenseSummary)
def summary(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> ExpenseSummary:
    return service.summary(db, org, property_id, from_date, to_date)


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get(expense_id: UUID, db: Database, org: OrganizationContext) -> Expense:
    return service.get(db, org, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update(expense_id: UUID, body: ExpensePatch, db: Database, org: OrganizationContext) -> Expense:
    return service.update(db, org, expense_id, body)


@router.delete("/{expense_id}", status_code=204)
def delete(expense_id: UUID, db: Database, org: OrganizationContext) -> Response:
    service.delete(db, org, expense_id)
    return Response(status_code=204)
