from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories import events as repo
from app.repositories.market import property_region
from app.schemas.events import EventItem, EventMarket, EventScope, EventSummary
from app.services.foundation import get_property
from app.services.market import today_seoul


def events(
    db: Session,
    org: UUID,
    property_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 50,
) -> EventMarket:
    get_property(db, org, property_id)
    today = today_seoul()
    start = from_date or today
    try:
        end = to_date or (start + timedelta(days=90))
    except OverflowError:
        raise HTTPException(422, "Invalid event date") from None
    if not 0 <= (end - start).days <= 180 or not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid event window or limit")
    result = EventMarket(
        property_id=property_id, from_date=start, to_date=end, reference_date=today
    )
    region = property_region(db, org, property_id)
    if region is None:
        result.reason = "PROPERTY_REGION_UNAVAILABLE"
        return result
    result.scope = EventScope(name=region.sido_name + " " + region.sigungu_name)
    latest = repo.latest_run(db)
    success = repo.latest_run(db, completed=True)
    result.source.latest_sync_status = latest.status if latest else None
    if success is None or not success.event_coverage:
        result.reason = "NOT_SYNCHRONIZED"
        return result
    coverage_start = date.fromisoformat(str(success.event_coverage["start"]))
    coverage_end = date.fromisoformat(str(success.event_coverage["end"]))
    result.source.collected_at = success.collected_at
    result.source.coverage_start, result.source.coverage_end = coverage_start, coverage_end
    if start < coverage_start or end > coverage_end:
        result.reason = "OUTSIDE_COLLECTED_WINDOW"
        return result
    if latest and latest.status == "FAILED":
        result.warnings.append("최근 행사 수집에 실패했습니다. 마지막 성공 자료를 표시합니다.")
    result.warnings.append(
        "일정 변경·취소가 늦게 반영되거나 이전 자료가 남아 있을 수 있습니다. "
        "방문 전 주최 측에 확인해 주세요."
    )
    rows, total = repo.read(db, region.id, start, end, today, limit)
    result.events = [
        EventItem(
            source_event_id=r.source_event_id,
            title=r.title,
            start_date=r.start_date,
            end_date=r.end_date,
            temporal_status="UPCOMING"
            if r.start_date > today
            else "PAST"
            if r.end_date < today
            else "ONGOING",
            address=r.address,
            source_status=r.source_status,
            last_seen_at=r.last_seen_at,
        )
        for r in rows
    ]
    result.total_count = total
    result.truncated = total > len(rows)
    if coverage_start <= today and today + timedelta(days=30) <= coverage_end:
        ongoing, future = repo.counts(db, region.id, today, today + timedelta(days=30))
        result.summary = EventSummary(ongoing_count=ongoing, next_30_days_count=future)
    result.available = True
    return result
