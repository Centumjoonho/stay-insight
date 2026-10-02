from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.models.events import TourismEvent
from app.models.market import PublicDataSyncRun
from app.providers.events import DATASET, REGIONS, SOURCE, EventError, EventRecord
from app.repositories import events as repo
from app.services.market import today_seoul


class EventProvider(Protocol):
    def fetch(self, start: date, end: date) -> list[EventRecord]: ...


def synchronize(
    engine: Engine, provider: EventProvider, *, today: date | None = None
) -> PublicDataSyncRun:
    today = today or today_seoul()
    start, end = today - timedelta(days=30), today + timedelta(days=180)
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
                mapping = repo.regions(db)
                records = provider.fetch(start, end)
                ids = [r.source_event_id for r in records]
                if len(ids) != len(set(ids)) or any(
                    r.district not in mapping
                    or r.end_date < r.start_date
                    or r.end_date < start
                    or r.start_date > end
                    for r in records
                ):
                    raise EventError("EVENT_INVALID_BATCH")
                old = repo.existing(db)
                now = datetime.now(UTC)
                for r in records:
                    values = dict(
                        source=SOURCE,
                        source_dataset=DATASET,
                        source_event_id=r.source_event_id,
                        region_id=mapping[r.district],
                        source_region_code="26",
                        source_sigungu_code=r.district,
                        title=r.title,
                        start_date=r.start_date,
                        end_date=r.end_date,
                        address=r.address,
                        source_status=r.source_status,
                    )
                    row = old.get(r.source_event_id)
                    if row is None:
                        db.add(TourismEvent(**values, last_seen_at=now, collected_at=now))
                        run.inserted_count += 1
                    else:
                        changed = any(getattr(row, k) != v for k, v in values.items())
                        for key, value in values.items():
                            setattr(row, key, value)
                        row.last_seen_at = row.collected_at = now
                        if changed:
                            row.updated_at = now
                            run.updated_count += 1
                        else:
                            run.unchanged_count += 1
                run.fetched_count = len(records)
                run.covered_districts = list(REGIONS.values())
                run.event_coverage = {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "completeness": "SOURCE_QUERY_ONLY",
                }
                run.collected_at = run.completed_at = now
                run.status = "COMPLETED"
        except Exception as error:
            with db.begin():
                db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
                run.status = "FAILED"
                run.completed_at = datetime.now(UTC)
                run.inserted_count = run.updated_count = run.unchanged_count = 0
                run.failed_count = 1
                safe = {
                    "EVENT_ALREADY_RUNNING",
                    "EVENT_REGION_MAPPING_INVALID",
                    "EVENT_INVALID_BATCH",
                    "EVENT_KEY_REQUIRED",
                    "EVENT_INVALID_RESPONSE",
                    "EVENT_EMPTY_CONTRACT_UNVERIFIED",
                    "EVENT_RESPONSE_TOO_LARGE",
                    "EVENT_HTTP_ERROR",
                    "EVENT_NETWORK_ERROR",
                    "EVENT_INVALID_WINDOW",
                    "EVENT_SNAPSHOT_CHANGED",
                    "EVENT_DUPLICATE_ID",
                    "EVENT_OUTSIDE_WINDOW",
                    "EVENT_PAGE_LIMIT",
                }
                run.error_summary = (
                    str(error)
                    if isinstance(error, EventError) and str(error) in safe
                    else "EVENT_SYNC_FAILED"
                )
        return run
