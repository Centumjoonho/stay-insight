"""Manual local bootstrap/refresh. Safe status only; no raw exceptions."""

import argparse
import json
import os

from sqlalchemy import create_engine

from app.providers.visitor_api import OfficialVisitorProvider
from app.services.visitor_sync import synchronize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    url = os.environ.get("MARKET_DATABASE_URL")
    if not url:
        print(json.dumps({"status": "FAILED", "error": "MARKET_DATABASE_URL_REQUIRED"}))
        return 1
    engine = None
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        run = synchronize(
            engine,
            OfficialVisitorProvider(os.environ.get("TOURISM_VISITOR_API_KEY", "")),
            bootstrap=args.bootstrap,
            lookback=int(os.environ.get("TOURISM_VISITOR_LOOKBACK_DAYS", "60")),
            refresh_days=int(os.environ.get("TOURISM_VISITOR_REFRESH_DAYS", "35")),
        )
        print(
            json.dumps(
                {
                    "id": str(run.id),
                    "status": run.status,
                    "inserted": run.inserted_count,
                    "updated": run.updated_count,
                    "unchanged": run.unchanged_count,
                    "latest_reference_date": str(run.source_reference_date)
                    if run.source_reference_date
                    else None,
                    "missing_pairs": (run.visitor_coverage or {}).get("missing_pair_count"),
                    "error": run.error_summary,
                }
            )
        )
        return 0 if run.status == "COMPLETED" else 1
    except Exception:
        print(json.dumps({"status": "FAILED", "error": "VISITOR_CONFIGURATION_OR_DATABASE_ERROR"}))
        return 1
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
