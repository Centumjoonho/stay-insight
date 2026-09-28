from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.providers.accommodation import DATASET, SOURCE, SOURCE_URL
from app.repositories import market as repo
from app.schemas.market import AccommodationMarket, MarketFreshness, MarketMetrics, MarketRegion
from app.services.foundation import get_property


def today_seoul() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def window_start(reference: date) -> date:
    # (same calendar date one year ago, reference], with Feb 29 clamped to Feb 28.
    return date(
        reference.year - 1,
        reference.month,
        min(reference.day, monthrange(reference.year - 1, reference.month)[1]),
    ) + timedelta(days=1)


def accommodations(
    db: Session, org: UUID, property_id: UUID, reference: date | None = None
) -> AccommodationMarket:
    get_property(db, org, property_id)
    reference = reference or today_seoul()
    if reference < date(1901, 1, 1) or reference > today_seoul():
        raise HTTPException(422, "Reference date must be between 1901-01-01 and today")
    result = AccommodationMarket(
        property_id=property_id,
        reference_date=reference,
        window_start=window_start(reference),
        window_end=reference,
        freshness=MarketFreshness(
            source=SOURCE,
            source_dataset_name=DATASET,
            source_url=SOURCE_URL,
            live_provider_verified=True,
        ),
    )
    region = repo.property_region(db, org, property_id)
    if region is None:
        result.reason = "PROPERTY_REGION_UNAVAILABLE"
        return result
    result.region = MarketRegion(scope_name=region.sido_name + " " + region.sigungu_name)
    latest = repo.latest_run(db)
    successful = repo.latest_run(db, completed=True, district=region.sigungu_name)
    result.freshness.latest_sync_status = latest.status if latest else None
    if not successful or region.sigungu_name not in successful.covered_districts:
        result.reason = "NOT_SYNCHRONIZED"
        return result
    result.freshness.collected_at = successful.collected_at
    result.freshness.source_reference_date = successful.source_reference_date
    now = datetime.now(UTC)
    result.freshness.stale = bool(
        successful.collected_at
        and now - successful.collected_at > timedelta(days=7)
        or successful.source_reference_date
        and (today_seoul() - successful.source_reference_date).days > 7
    )
    data = repo.counts(db, region.id, result.window_start, reference)
    result.metrics = MarketMetrics(
        open_businesses=data["open"],
        new_licenses_12m=data["new"] if not data["missing_license_dates"] else None,
        closures_12m=data["closed"]
        if successful.closure_dates_supported and not data["missing_closure_dates"]
        else None,
        type_breakdown=repo.type_counts(db, region.id),
        unknown_status_count=data["unknown"],
        missing_license_dates=data["missing_license_dates"],
        missing_closure_dates=data["missing_closure_dates"],
    )
    result.market_context_available = True
    result.warnings.append(
        "영업 상태와 업종 구성은 최신 수집 자료 기준이며 과거 시점의 영업 상태가 아닙니다."
    )
    result.warnings.append(
        "단일 숙박업 인허가 자료의 등록 건수이며 전체 숙박시설 수나 객실 수가 아닙니다."
    )
    result.warnings.append("이전 수집 뒤 누락된 기록은 폐업으로 추정하거나 삭제하지 않습니다.")
    if latest and latest.status == "FAILED":
        result.warnings.append("최근 수집에 실패하여 마지막 성공 자료를 표시합니다.")
    if data["unknown"]:
        result.warnings.append("영업 상태 미확인 기록은 영업 중 건수에서 제외됩니다.")
    return result
