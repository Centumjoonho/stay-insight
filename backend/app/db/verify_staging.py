"""Read-only role and transaction checks over the actual selected connection mode."""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.services.readiness import ready


def verify_ingestion(url: str) -> bool:
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.begin() as db:
            unsafe = db.scalar(
                text("""SELECT rolsuper OR rolbypassrls OR rolcreaterole
                OR rolcreatedb FROM pg_roles WHERE rolname=current_user""")
            )
            if unsafe is not False:
                return False
            if db.scalar(
                text("SELECT has_table_privilege(current_user,'app.reservations','SELECT')")
            ):
                return False
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            if not db.scalar(
                text("""SELECT
                has_table_privilege(
                    current_user,'app.public_accommodation_licenses','INSERT')
                AND has_table_privilege(
                    current_user,'app.public_accommodation_licenses','UPDATE')
                AND NOT has_table_privilege(current_user,'app.expenses','SELECT')""")
            ):
                return False
        with engine.begin() as db:
            return db.scalar(text("SELECT current_user=session_user")) is True
    finally:
        engine.dispose()


def main() -> int:
    try:
        if os.environ.get("APP_ENV") != "staging":
            raise ValueError("Staging only")
        runtime, collector = os.environ["DATABASE_URL"], os.environ["MARKET_DATABASE_URL"]
        for value in (runtime, collector):
            url = make_url(value)
            if url.port == 6543 or url.query.get("sslmode") not in {
                "require",
                "verify-ca",
                "verify-full",
            }:
                raise ValueError("Verified direct/session TLS connection required")
        engine = create_engine(
            runtime, pool_size=1, max_overflow=0, connect_args={"connect_timeout": 5}
        )
        try:
            if not ready(engine):
                raise ValueError("Runtime readiness failed")
            with engine.begin() as db:
                db.execute(
                    text("SELECT set_config('app.organization_id', :v, true)"),
                    {"v": "00000000-0000-0000-0000-000000000001"},
                )
                if db.scalar(text("SELECT count(*) FROM app.reservations")) != 0:
                    raise ValueError("Missing user context must hide rows")
            with engine.begin() as db:
                if db.scalar(text("SELECT nullif(current_setting('app.organization_id',true),'')")):
                    raise ValueError("Pooled transaction context leaked")
        finally:
            engine.dispose()
        if not verify_ingestion(collector):
            raise ValueError("Ingestion boundary failed")
        print("STAGING_ROLE_AND_CONNECTION_CHECKS_PASSED")
        return 0
    except Exception:
        print("STAGING_VERIFICATION_FAILED: check private connection and role setup")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
