"""Versioned operational denominators; shared frozen v1 financial and comparison rules."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories import dashboard as repo
from app.repositories import dashboard_v2 as inventory_repo
from app.schemas.dashboard import DashboardProperty, Period, Warning
from app.schemas.dashboard_v2 import (
    DashboardSummaryV2,
    DashboardTrendsV2,
    InventoryQuality,
    MetricsV2,
    ProvenanceV2,
    TrendRowV2,
)
from app.services.dashboard import (
    compare,
    metrics,
    period_for,
    ratio,
    selected_period,
    shift_month,
    today_seoul,
)
from app.services.foundation import get_property


def metrics_v2(
    period: Period,
    data: repo.Aggregate,
    fallback: int,
    inventory: inventory_repo.InventoryAggregate,
) -> MetricsV2:
    base = metrics(period, data, fallback)
    operations = base.operations.model_copy(
        update={
            "occupied_room_nights": inventory.occupied,
            "available_room_nights": inventory.available,
            "occupancy_rate": ratio(Decimal(inventory.occupied), inventory.available, 100),
            "adr": ratio(data.allocated, inventory.occupied),
            "revpar": ratio(data.allocated, inventory.available),
        }
    )
    quality = InventoryQuality(
        **base.data_quality.model_dump(),
        missing_room_units_count=inventory.missing_room_units,
        capacity_fallback_days=inventory.fallback_days,
        unrecorded_unavailability_days=inventory.unrecorded_days,
        overcapacity_days=inventory.overcapacity_days,
    )
    quality.warnings = [
        w for w in quality.warnings if w.code not in {"OCCUPANCY_OVER_100", "INVALID_INVENTORY"}
    ]

    def warn(code: str, message: str) -> None:
        quality.warnings.append(Warning(code=code, message=message))

    if inventory.missing_room_units:
        warn(
            "MISSING_ROOM_UNITS",
            f"객실 수가 입력되지 않은 예약 {inventory.missing_room_units}건은 "
            "1객실로 추정했습니다.",
        )
    if inventory.fallback_days:
        warn(
            "CAPACITY_FALLBACK",
            f"객실 수 이력이 없는 {inventory.fallback_days}일은 숙소 기본 객실 수로 추정했습니다.",
        )
    if inventory.unrecorded_days:
        warn(
            "UNRECORDED_UNAVAILABILITY",
            f"판매 제외 기록이 없는 {inventory.unrecorded_days}일은 제외 0실로 계산했습니다.",
        )
    if inventory.overcapacity_days:
        warn(
            "OVERCAPACITY",
            f"예약 객실 수가 가용 객실 수를 초과한 날짜가 {inventory.overcapacity_days}일입니다. "
            "객실 수와 예약을 확인해 주세요.",
        )
    if inventory.available <= 0:
        warn("ZERO_AVAILABILITY", "가용 객실박이 0이므로 점유율과 RevPAR를 계산할 수 없습니다.")
    return MetricsV2(
        **base.model_dump(exclude={"operations", "data_quality"}),
        operations=operations,
        data_quality=quality,
    )


def summary(db: Session, org: UUID, property_id: UUID, month: str | None) -> DashboardSummaryV2:
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
    inventory = inventory_repo.aggregate(db, org, property_id, periods, prop.inventory_units)
    results = {
        key: metrics_v2(period, data[key], prop.inventory_units, inventory[key])
        for key, period in periods.items()
    }
    return DashboardSummaryV2(
        **results["selected"].model_dump(),
        property=DashboardProperty(
            id=prop.id, name=prop.name, inventory_units=prop.inventory_units
        ),
        metadata=ProvenanceV2(generated_at=datetime.now(UTC)),
        comparisons={
            key: compare(results["selected"], results[key])
            for key in ("previous_month", "previous_year")
        },
    )


def trends(
    db: Session, org: UUID, property_id: UUID, months: int, month: str | None
) -> DashboardTrendsV2:
    prop = get_property(db, org, property_id)
    today = today_seoul()
    end = selected_period(month, today)
    periods = {
        str(i): period_for(shift_month(end.start_date, i), today) for i in range(1 - months, 1)
    }
    data = repo.aggregate(db, org, property_id, periods)
    inventory = inventory_repo.aggregate(db, org, property_id, periods, prop.inventory_units)
    items: list[TrendRowV2] = []
    for key, period in periods.items():
        result = metrics_v2(period, data[key], prop.inventory_units, inventory[key])
        items.append(
            TrendRowV2(
                data_quality=result.data_quality,
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
    return DashboardTrendsV2(
        property=DashboardProperty(
            id=prop.id, name=prop.name, inventory_units=prop.inventory_units
        ),
        metadata=ProvenanceV2(generated_at=datetime.now(UTC)),
        items=items,
    )
