"""Command-only atomic publication. Providers do not run in HTTP request handling."""

from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.models.market import PublicAccommodationLicense, PublicDataSyncRun
from app.providers.accommodation import SOURCE, AccommodationProvider, ProviderUnavailable
from app.repositories import market as repo


def synchronize(engine: Engine, provider: AccommodationProvider) -> PublicDataSyncRun:
    run = PublicDataSyncRun(
        id=uuid4(), source=SOURCE, status="RUNNING", started_at=datetime.now(UTC)
    )
    fetched = failed = 0
    with Session(engine, expire_on_commit=False) as db:
        with db.begin():
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            db.add(run)
        try:
            with db.begin():
                db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
                repo.lock_sync(db)
                batch = provider.fetch()
                run.fetched_count = len(batch.records) + batch.failed_count
                run.failed_count = batch.failed_count
                fetched, failed = run.fetched_count, run.failed_count
                region_map = repo.regions(db)
                covered = set(batch.covered_districts)
                ids = [record.source_record_id for record in batch.records]
                if (
                    not batch.complete
                    or batch.failed_count
                    or not covered
                    or not covered <= region_map.keys()
                    or len(set(ids)) != len(ids)
                    or any(r.sigungu_name not in covered for r in batch.records)
                ):
                    raise ProviderUnavailable("INCOMPLETE_OR_INVALID_BATCH")
                if (
                    batch.source_reference_date
                    and batch.source_reference_date > datetime.now(ZoneInfo("Asia/Seoul")).date()
                ):
                    raise ProviderUnavailable("INVALID_SOURCE_DATE")
                # Refuse source-reference regression rather than overwrite newer observations.
                previous = repo.latest_run(db, completed=True)
                if (
                    previous
                    and previous.source_reference_date
                    and batch.source_reference_date
                    and batch.source_reference_date < previous.source_reference_date
                ):
                    raise ProviderUnavailable("OLDER_SOURCE_BATCH")
                collected = datetime.now(UTC)
                stored = repo.existing(db)
                for record in batch.records:
                    values = repo.record_values(record, region_map[record.sigungu_name].id)
                    item = stored.get(record.source_record_id)
                    if item is None:
                        db.add(PublicAccommodationLicense(**values, collected_at=collected))
                        run.inserted_count += 1
                    else:
                        if any(getattr(item, key) != value for key, value in values.items()):
                            for key, value in values.items():
                                setattr(item, key, value)
                            item.updated_at = collected
                            run.updated_count += 1
                        else:
                            run.unchanged_count += 1
                        item.collected_at = collected
                # Absence is not a closure or deletion. Historical rows are retained.
                run.covered_districts = sorted(covered)
                run.source_reference_date = batch.source_reference_date
                run.closure_dates_supported = batch.closure_dates_supported
                run.collected_at = collected
                run.status = "COMPLETED"
                run.completed_at = collected
        except Exception as error:
            # Never persist raw exception text (URLs, credentials or source payloads).
            with db.begin():
                db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
                run.status = "FAILED"
                run.completed_at = datetime.now(UTC)
                run.inserted_count = run.updated_count = run.unchanged_count = 0
                run.fetched_count = fetched
                run.failed_count = max(failed, 1)
                run.error_summary = (
                    str(error)
                    if isinstance(error, ProviderUnavailable)
                    and str(error)
                    in {
                        "API_KEY_REQUIRED",
                        "API_HTTP_ERROR",
                        "API_NETWORK_ERROR",
                        "API_INVALID_RESPONSE",
                        "API_RESULT_ERROR",
                        "API_RESPONSE_TOO_LARGE",
                        "API_INCOMPLETE_PAGE",
                        "API_SNAPSHOT_CHANGED",
                        "API_DUPLICATE_RECORD",
                        "INCOMPLETE_OR_INVALID_BATCH",
                        "INVALID_SOURCE_DATE",
                        "OLDER_SOURCE_BATCH",
                    }
                    else "SYNC_FAILED"
                )
        return run
