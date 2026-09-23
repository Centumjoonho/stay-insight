import calendar
import re
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.expenses import ExpenseCategory
from app.repositories import dashboard as repo
from app.schemas.dashboard import (
    ChannelRow,
    Comparison,
    DashboardProperty,
    DashboardSummary,
    DashboardTrends,
    DataQuality,
    Delta,
    Financial,
    Metrics,
    Operations,
    Period,
    Provenance,
    TrendRow,
    Warning,
)
from app.schemas.expenses import CategoryTotal
from app.services.foundation import get_property


def today_seoul() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def shift_month(value: date, offset: int) -> date:
    year, month = divmod(value.year * 12 + value.month - 1 + offset, 12)
    return date(year, month + 1, 1)


def period_for(start: date, today: date, day_limit: int | None = None) -> Period:
    last = calendar.monthrange(start.year, start.month)[1]
    current = start == today.replace(day=1)
    day = min(last, today.day if current else day_limit or last)
    return Period(
        month=start.strftime("%Y-%m"),
        start_date=start,
        end_date=start.replace(day=day),
        is_current_month=current,
        is_partial=day < last,
    )


def selected_period(month: str | None, today: date) -> Period:
    month = month or today.strftime("%Y-%m")
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(422, "month must be YYYY-MM")
    year, number = map(int, month.split("-"))
    if year < 1901:
        raise HTTPException(422, "month must be 1901-01 or later")
    start = date(year, number, 1)
    if start > today.replace(day=1):
        raise HTTPException(422, "Future forecasting is not supported")
    return period_for(start, today)


def rounded(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def ratio(numerator: Decimal, denominator: Decimal | int, multiplier: int = 1) -> Decimal | None:
    if denominator <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        return rounded(numerator / Decimal(denominator) * multiplier)


def operational_values(
    occupied: int, allocated: Decimal, inventory: int, days: int
) -> tuple[int, Decimal | None, Decimal | None, Decimal | None]:
    available = max(inventory, 0) * max(days, 0)
    return (
        available,
        ratio(Decimal(occupied), available, 100),
        ratio(allocated, occupied),
        ratio(allocated, available),
    )


def metrics(period: Period, data: repo.Aggregate, inventory: int) -> Metrics:
    # Decimal precision accommodates exact aggregates beyond any individual NUMERIC(18,0).
    with localcontext() as ctx:
        ctx.prec = 50
        return _metrics(period, data, inventory)


def _metrics(period: Period, data: repo.Aggregate, inventory: int) -> Metrics:
    revenue = sum((c.revenue for c in data.channels), Decimal(0))
    count = sum(c.count for c in data.channels)
    known = sum(c.fee_count for c in data.channels)
    fee = sum((c.fee for c in data.channels), Decimal(0))
    nights = sum(c.nights for c in data.channels)
    unknown = sum(c.unknown for c in data.channels)
    cancelled = sum(c.cancelled for c in data.channels)
    fixed = sum((amount for _, kind, amount, _ in data.expenses if kind == "FIXED"), Decimal(0))
    variable = sum(
        (amount for _, kind, amount, _ in data.expenses if kind == "VARIABLE"), Decimal(0)
    )
    expense_count = sum(n for _, _, _, n in data.expenses)
    manual = fixed + variable
    cost = manual + fee
    profit = revenue - cost
    available, occupancy, adr, revpar = operational_values(
        data.occupied, data.allocated, inventory, (period.end_date - period.start_date).days + 1
    )
    warnings: list[Warning] = []

    def warn(code: str, message: str) -> None:
        warnings.append(Warning(code=code, message=message))

    if unknown or data.overlapping_unknown:
        warn("UNKNOWN_STATUS", "상태 미확인 예약을 포함합니다. 예약 상태를 확인해 주세요.")
    if count > known:
        warn("MISSING_CHANNEL_FEE", f"플랫폼 수수료 정보가 없는 예약 {count - known}건")
    if occupancy is not None and occupancy > 100:
        warn(
            "OCCUPANCY_OVER_100",
            "점유율이 100%를 초과합니다. 객실 수와 중복·겹친 예약을 확인해 주세요.",
        )
    if not count and not data.overlapping:
        warn("NO_RESERVATIONS", "아직 분석할 예약 데이터가 없습니다.")
    if not expense_count:
        warn("NO_EXPENSES", "등록된 운영비가 없습니다.")
    if inventory <= 0:
        warn("INVALID_INVENTORY", "등록 객실 수를 확인해 주세요.")
    if cancelled:
        warn(
            "CANCELLED_EXCLUDED",
            "취소 예약을 제외하므로 비용 관리 화면의 수수료 합계와 다를 수 있습니다.",
        )
    categories: dict[str, Decimal] = {}
    for category, _, amount, _ in data.expenses:
        categories[category] = categories.get(category, Decimal(0)) + amount
    return Metrics(
        period=period,
        financial=Financial(
            recognized_gross_revenue=revenue,
            manual_expense_total=manual,
            fixed_expense_total=fixed,
            variable_expense_total=variable,
            known_channel_fee_total=fee,
            known_cost_total=cost,
            known_operating_profit=profit,
            known_operating_margin=ratio(profit, revenue, 100),
        ),
        operations=Operations(
            reservation_count=count,
            occupied_room_nights=data.occupied,
            available_room_nights=available,
            occupancy_rate=occupancy,
            allocated_operational_revenue=rounded(data.allocated, "0.000001"),
            adr=adr,
            revpar=revpar,
            average_length_of_stay=ratio(Decimal(nights), count),
            overlapping_reservation_count=data.overlapping,
        ),
        data_quality=DataQuality(
            unknown_status_count=unknown,
            overlapping_unknown_status_count=data.overlapping_unknown,
            cancelled_reservation_count=cancelled,
            channel_fee_known_count=known,
            channel_fee_missing_count=count - known,
            expense_count=expense_count,
            has_financial_reservations=count > 0,
            has_operational_reservations=data.overlapping > 0,
            warnings=warnings,
        ),
        channels=[
            ChannelRow(
                channel=c.channel,
                reservation_count=c.count,
                recognized_gross_revenue=c.revenue,
                known_channel_fee=c.fee if c.fee_count else None,
                channel_fee_known_count=c.fee_count,
                channel_fee_missing_count=c.count - c.fee_count,
                booked_nights=c.nights,
                revenue_share_percent=ratio(c.revenue, revenue, 100),
            )
            for c in sorted(data.channels, key=lambda c: c.channel)
            if c.count
        ],
        category_breakdown=[
            CategoryTotal(category=ExpenseCategory(c), amount=a)
            for c, a in sorted(categories.items())
        ],
    )


def delta(
    current: Decimal | int | None,
    baseline: Decimal | int | None,
    available: bool,
    points: bool = False,
) -> Delta:
    if not available or current is None or baseline is None:
        return Delta(
            available=False, absolute_delta=None, percentage_change=None, percentage_points=None
        )
    with localcontext() as ctx:
        ctx.prec = 50
        change = Decimal(current) - Decimal(baseline)
        return Delta(
            available=True,
            absolute_delta=change,
            percentage_change=None if points else ratio(change, baseline, 100),
            percentage_points=change if points else None,
        )


def compare(current: Metrics, baseline: Metrics) -> Comparison:
    financial = (
        "recognized_gross_revenue",
        "manual_expense_total",
        "fixed_expense_total",
        "variable_expense_total",
        "known_channel_fee_total",
        "known_cost_total",
        "known_operating_profit",
        "known_operating_margin",
    )
    operational = (
        "reservation_count",
        "occupied_room_nights",
        "occupancy_rate",
        "adr",
        "revpar",
        "average_length_of_stay",
    )
    changes: dict[str, Delta] = {}
    for key in financial + operational:
        if key in ("manual_expense_total", "fixed_expense_total", "variable_expense_total"):
            exists = (
                current.data_quality.expense_count > 0 and baseline.data_quality.expense_count > 0
            )
        elif key in ("occupied_room_nights", "occupancy_rate", "adr", "revpar"):
            exists = (
                current.data_quality.has_operational_reservations
                and baseline.data_quality.has_operational_reservations
            )
        elif key == "known_channel_fee_total":
            exists = (
                current.data_quality.channel_fee_known_count > 0
                and baseline.data_quality.channel_fee_known_count > 0
            )
        elif key == "known_cost_total":
            exists = (
                current.data_quality.expense_count + current.data_quality.channel_fee_known_count
                > 0
                and baseline.data_quality.expense_count
                + baseline.data_quality.channel_fee_known_count
                > 0
            )
        else:
            exists = (
                current.data_quality.has_financial_reservations
                and baseline.data_quality.has_financial_reservations
            )
        a = getattr(current.financial if key in financial else current.operations, key)
        b = getattr(baseline.financial if key in financial else baseline.operations, key)
        changes[key] = delta(a, b, exists, key in ("occupancy_rate", "known_operating_margin"))
    return Comparison(period=baseline.period, metrics=changes)


def summary(db: Session, org: UUID, property_id: UUID, month: str | None) -> DashboardSummary:
    prop = get_property(db, org, property_id)
    today = today_seoul()
    current = selected_period(month, today)
    day_limit = current.end_date.day if current.is_current_month and current.is_partial else None
    periods = {
        "selected": current,
        "previous_month": period_for(shift_month(current.start_date, -1), today, day_limit),
        "previous_year": period_for(shift_month(current.start_date, -12), today, day_limit),
    }
    data = repo.aggregate(db, org, property_id, periods)
    results = {
        key: metrics(period, data[key], prop.inventory_units) for key, period in periods.items()
    }
    return DashboardSummary(
        **results["selected"].model_dump(),
        property=DashboardProperty(
            id=prop.id, name=prop.name, inventory_units=prop.inventory_units
        ),
        metadata=Provenance(generated_at=datetime.now(UTC)),
        comparisons={
            key: compare(results["selected"], results[key])
            for key in ("previous_month", "previous_year")
        },
    )


def trends(
    db: Session, org: UUID, property_id: UUID, months: int, month: str | None
) -> DashboardTrends:
    prop = get_property(db, org, property_id)
    today = today_seoul()
    end = selected_period(month, today)
    periods = {
        str(i): period_for(shift_month(end.start_date, i), today) for i in range(1 - months, 1)
    }
    data = repo.aggregate(db, org, property_id, periods)
    items: list[TrendRow] = []
    for key, period in periods.items():
        result = metrics(period, data[key], prop.inventory_units)
        items.append(
            TrendRow(
                month=period.month,
                end_date=period.end_date,
                is_partial=period.is_partial,
                recognized_gross_revenue=result.financial.recognized_gross_revenue,
                manual_expense_total=result.financial.manual_expense_total,
                known_channel_fee_total=result.financial.known_channel_fee_total,
                known_cost_total=result.financial.known_cost_total,
                known_operating_profit=result.financial.known_operating_profit,
                occupancy_rate=result.operations.occupancy_rate,
                adr=result.operations.adr,
                revpar=result.operations.revpar,
                reservation_count=result.operations.reservation_count,
                has_financial_reservations=result.data_quality.has_financial_reservations,
                has_operational_reservations=result.data_quality.has_operational_reservations,
                expense_count=result.data_quality.expense_count,
            )
        )
    return DashboardTrends(
        property=DashboardProperty(
            id=prop.id, name=prop.name, inventory_units=prop.inventory_units
        ),
        metadata=Provenance(generated_at=datetime.now(UTC)),
        items=items,
    )
