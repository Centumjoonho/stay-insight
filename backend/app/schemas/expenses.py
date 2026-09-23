from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.models.expenses import CostType, ExpenseCategory


def exact_amount(value: object) -> object:
    # JSON integer or decimal string only: reject floats before precision can be lost.
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Use integer KRW or an exact decimal string")
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(exact_amount),
    Field(ge=0, max_digits=18, decimal_places=0, allow_inf_nan=False),
]


class ExpenseValues(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expense_date: date
    category: ExpenseCategory
    cost_type: CostType
    amount: Money
    memo: str | None = Field(None, max_length=1000)


class ExpenseCreate(ExpenseValues):
    property_id: UUID


class ExpensePatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expense_date: date | None = None
    category: ExpenseCategory | None = None
    cost_type: CostType | None = None
    amount: Money | None = None
    memo: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def valid_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one change is required")
        if any(getattr(self, key) is None for key in self.model_fields_set - {"memo"}):
            raise ValueError("Required values cannot be null")
        return self


class ExpenseResponse(ExpenseValues):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    property_id: UUID
    source: Literal["MANUAL"]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ExpenseList(BaseModel):
    items: list[ExpenseResponse]
    total: int


class CategoryTotal(BaseModel):
    category: ExpenseCategory
    amount: Decimal


class CostTypeTotal(BaseModel):
    cost_type: CostType
    amount: Decimal


class ExpenseSummary(BaseModel):
    property_id: UUID
    from_date: date
    to_date: date
    manual_expense_total: Decimal
    fixed_expense_total: Decimal
    variable_expense_total: Decimal
    channel_fee_total: Decimal
    known_cost_total: Decimal
    category_breakdown: list[CategoryTotal]
    cost_type_breakdown: list[CostTypeTotal]
    reservations_with_fee: int
    reservations_missing_fee: int
    manual_source: Literal["MANUAL"] = "MANUAL"
    channel_fee_source: Literal["owner_csv"] = "owner_csv"
    channel_fee_date_basis: Literal["check_in"] = "check_in"
    is_estimated: Literal[False] = False
