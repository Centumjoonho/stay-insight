"""Manual event sync; emit only fixed errors and aggregate counts."""

import json
import os

from sqlalchemy import create_engine

from app.providers.events import OfficialEventProvider
from app.services.event_sync import synchronize


def main() -> int:
    url = os.environ.get("MARKET_DATABASE_URL")
    if not url:
        print(json.dumps({"status": "FAILED", "error": "MARKET_DATABASE_URL_REQUIRED"}))
        return 1
    engine = None
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        run = synchronize(
            engine, OfficialEventProvider(os.environ.get("TOURISM_EVENT_API_KEY", ""))
        )
        print(
            json.dumps(
                {
                    "id": str(run.id),
                    "status": run.status,
                    "fetched": run.fetched_count,
                    "inserted": run.inserted_count,
                    "updated": run.updated_count,
                    "unchanged": run.unchanged_count,
                    "failed": run.failed_count,
                    "error": run.error_summary,
                }
            )
        )
        return 0 if run.status == "COMPLETED" else 1
    except Exception:
        print(json.dumps({"status": "FAILED", "error": "EVENT_CONFIGURATION_OR_DATABASE_ERROR"}))
        return 1
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
