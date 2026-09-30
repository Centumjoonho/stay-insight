"""One dataset lock, bounded collection, atomic publication; no tenant reads."""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.models.market import PublicDataSyncRun
from app.models.visitors import VisitorDaily
from app.providers.tourism_visitors import DATASET
from app.providers.visitor_api import (
    CATEGORIES,
    REGIONS,
    SOURCE,
    VisitorError,
    VisitorRecord,
)
from app.repositories import visitors as repo


class DailyProvider(Protocol):
    def fetch_day(self, day: date) -> list[VisitorRecord]: ...


def synchronize(
    engine: Engine,
    provider: DailyProvider,
    *,
    bootstrap: bool = False,
    lookback: int = 60,
    refresh_days: int = 35,
    today: date | None = None,
) -> PublicDataSyncRun:
    run = PublicDataSyncRun(
        id=uuid4(), source=SOURCE, status="RUNNING", started_at=datetime.now(UTC)
    )
    with Session(engine, expire_on_commit=False) as db:
        with db.begin():
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            db.add(run)
        try:
            with db.begin():
                db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
                repo.lock_sync(db)
                regions = repo.resolve_regions(db)
                if not 1 <= lookback <= 120 or not 1 <= refresh_days <= 120:
                    raise VisitorError("VISITOR_INVALID_OPTIONS")
                today = today or datetime.now(ZoneInfo("Asia/Seoul")).date()
                batches: dict[date, list[VisitorRecord]] = {}
                latest = None
                # Today is excluded operationally; not a claim of D-1 availability.
                for offset in range(1, lookback + 1):
                    day = today - timedelta(days=offset)
                    batches[day] = provider.fetch_day(day)
                    if batches[day]:
                        latest = day
                        break
                if latest is None:
                    raise VisitorError("VISITOR_NO_DATA_IN_LOOKBACK")
                start = latest - timedelta(days=(120 if bootstrap else refresh_days) - 1)
                for offset in range((latest - start).days + 1):
                    day = start + timedelta(days=offset)
                    if day not in batches:
                        batches[day] = provider.fetch_day(day)
                # Include empty discovery days so withdrawn previously stored dates become missing.
                end = max(batches)
                old = {
                    (r.source_region_code, r.visitor_category_code, r.reference_date): r
                    for r in repo.existing(db, start, end)
                }
                expected = {(code, category) for code in REGIONS for category in CATEGORIES}
                missing: dict[str, list[str]] = {}
                seen: set[tuple[str, str, date]] = set()
                now = datetime.now(UTC)
                for day, records in batches.items():
                    pairs = set()
                    for r in records:
                        key = (r.code, r.category, r.day)
                        if (
                            r.day != day
                            or r.code not in REGIONS
                            or r.name != REGIONS[r.code]
                            or r.category not in CATEGORIES
                            or r.category_name != CATEGORIES[r.category]
                            or not r.value.is_finite()
                            or r.value < 0
                            or key in seen
                        ):
                            raise VisitorError("VISITOR_INVALID_BATCH")
                        seen.add(key)
                        pairs.add((r.code, r.category))
                        values = dict(
                            region_id=regions[r.code],
                            source=SOURCE,
                            source_dataset=DATASET,
                            source_region_code=r.code,
                            source_region_name=r.name,
                            visitor_category_code=r.category,
                            visitor_category_name=r.category_name,
                            reference_date=r.day,
                            visitor_value=r.value,
                            day_of_week_code=r.weekday,
                            day_of_week_name=r.weekday_name,
                        )
                        stored = old.get(key)
                        if stored is None:
                            db.add(VisitorDaily(**values, collected_at=now))
                            run.inserted_count += 1
                        else:
                            changed = any(getattr(stored, k) != v for k, v in values.items())
                            for k, v in values.items():
                                setattr(stored, k, v)
                            stored.collected_at = now
                            if changed:
                                stored.updated_at = now
                                run.updated_count += 1
                            else:
                                run.unchanged_count += 1
                    if pairs != expected:
                        missing[day.isoformat()] = [
                            c + ":" + k for c, k in sorted(expected - pairs)
                        ]
                for key, stored in old.items():
                    if key[2] in batches and key not in seen:
                        if stored.visitor_value is not None:
                            run.updated_count += 1
                            stored.updated_at = now
                        stored.visitor_value = None
                        stored.collected_at = now
                run.fetched_count = len(seen)
                run.visitor_coverage = {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "latest_observed_date": latest.isoformat(),
                    "missing_pairs": missing,
                    "missing_pair_count": sum(map(len, missing.values())),
                    "bootstrap": bootstrap,
                    "completeness": "APPLICATION_COVERAGE_ONLY",
                }
                run.source_reference_date = latest
                run.covered_districts = list(REGIONS.values())
                run.collected_at = now
                run.completed_at = now
                run.status = "COMPLETED"
        except Exception as error:
            with db.begin():
                db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
                run.status = "FAILED"
                run.completed_at = datetime.now(UTC)
                run.inserted_count = run.updated_count = run.unchanged_count = 0
                run.failed_count = 1
                allowed = {
                    "VISITOR_ALREADY_RUNNING",
                    "VISITOR_REGION_MAPPING_INVALID",
                    "VISITOR_INVALID_OPTIONS",
                    "VISITOR_NO_DATA_IN_LOOKBACK",
                    "VISITOR_INVALID_BATCH",
                    "VISITOR_INVALID_DATE",
                    "VISITOR_KEY_REQUIRED",
                    "VISITOR_REQUEST_BUDGET_EXCEEDED",
                    "VISITOR_RESPONSE_TOO_LARGE",
                    "VISITOR_HTTP_ERROR",
                    "VISITOR_NETWORK_ERROR",
                    "VISITOR_INVALID_RESPONSE",
                    "VISITOR_SNAPSHOT_CHANGED",
                    "VISITOR_DUPLICATE_ROW",
                    "VISITOR_PAGE_LIMIT",
                }
                run.error_summary = (
                    str(error)
                    if isinstance(error, VisitorError) and str(error) in allowed
                    else "VISITOR_SYNC_FAILED"
                )
        return run
