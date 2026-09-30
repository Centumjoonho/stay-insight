from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from uuid import UUID

from sqlalchemy.orm import Session

from app.providers.visitor_api import CATEGORIES, REGIONS
from app.repositories import market
from app.repositories import visitors as repo
from app.schemas.visitors import (
    Coverage,
    DailyPoint,
    Rolling,
    VisitorCategory,
    VisitorMarket,
    VisitorScope,
)
from app.services.foundation import get_property
from app.services.market import today_seoul


def average(values: dict[date, Decimal | None], end: date, days: int) -> Decimal | None:
    rows = [values.get(end - timedelta(days=i)) for i in range(days)]
    if any(v is None for v in rows):
        return None
    return sum((v for v in rows if v is not None), Decimal(0)) / days


def rolling_metrics(values: dict[date, Decimal | None], end: date) -> Rolling:
    with localcontext() as ctx:
        ctx.prec = 80
        current = average(values, end, 7)
        previous = average(values, end - timedelta(days=7), 7)
        longer = average(values, end, 28)
        change = (
            (current - previous) / previous * 100
            if current is not None and previous is not None and previous > 0
            else None
        )

        def rounded(v: Decimal | None) -> Decimal | None:
            return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if v is not None else None

        return Rolling(
            average_7d=rounded(current),
            average_28d=rounded(longer),
            previous_7d_average=rounded(previous),
            change_7d_percent=rounded(change),
        )


def visitors(
    db: Session, org: UUID, property_id: UUID, category: str = "2", days: int = 90
) -> VisitorMarket:
    get_property(db, org, property_id)
    result = VisitorMarket(
        property_id=property_id,
        category=VisitorCategory(code=category, name=CATEGORIES[category]),
        coverage=Coverage(requested_days=days),
    )
    region = market.property_region(db, org, property_id)
    if region is None:
        result.reason = "PROPERTY_REGION_UNAVAILABLE"
        return result
    code = next((code for code, name in REGIONS.items() if name == region.sigungu_name), None)
    if code is None:
        result.reason = "PROPERTY_REGION_UNAVAILABLE"
        return result
    result.scope = VisitorScope(
        name=region.sido_name + " " + region.sigungu_name, source_region_code=code
    )
    run = repo.latest_run(db)
    success = repo.latest_run(db, completed=True)
    result.source.latest_sync_status = run.status if run else None
    if run and run.status == "FAILED":
        result.warnings.append(
            "최근 방문자 수집에 실패했습니다. 저장된 마지막 성공 자료를 표시합니다."
        )
    latest = repo.latest_day(db, region.id, category)
    if latest is None or success is None:
        result.reason = "NOT_SYNCHRONIZED"
        return result
    rows = repo.observations(
        db, region.id, category, latest - timedelta(days=max(days, 28) - 1), latest
    )
    values = {row.reference_date: row.visitor_value for row in rows}
    result.latest = DailyPoint(date=latest, value=values[latest])
    result.rolling = rolling_metrics(values, latest)
    result.history = [
        DailyPoint(date=latest - timedelta(days=i), value=values.get(latest - timedelta(days=i)))
        for i in reversed(range(days))
    ]
    result.coverage.available_days = sum(p.value is not None for p in result.history)
    result.coverage.missing_days = days - result.coverage.available_days
    result.coverage.complete_7d = result.rolling.average_7d is not None
    result.coverage.complete_28d = result.rolling.average_28d is not None
    result.source.last_collected_at = max(row.collected_at for row in rows)
    result.source.latest_reference_date = latest
    result.source.days_since_latest_reference = (today_seoul() - latest).days
    if not result.coverage.complete_7d or not result.coverage.complete_28d:
        result.warnings.append(
            "연속된 날짜의 자료가 부족한 평균은 표시하지 않습니다. 누락은 0이 아닙니다."
        )
    result.warnings.append(
        "평균과 비교는 자체 계산한 일별 파생 지표이며 공식 월 방문자 수가 아닙니다."
    )
    result.available = True
    return result
