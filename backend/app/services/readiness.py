"""Read-only readiness: no tenant rows, provider calls, or migration privileges."""

from sqlalchemy import Engine, text

REQUIRED_TABLES = (
    "organizations",
    "organization_members",
    "properties",
    "reservation_imports",
    "reservations",
    "expenses",
    "regions",
    "public_accommodation_licenses",
    "public_data_sync_runs",
)
TENANT_TABLES = set(REQUIRED_TABLES[:6])


def ready(engine: Engine) -> bool:
    try:
        with engine.connect() as db, db.begin():
            db.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            unsafe = db.scalar(
                text("""SELECT rolsuper OR rolbypassrls OR rolcreaterole
                OR rolcreatedb OR EXISTS (SELECT 1 FROM pg_tables
                WHERE schemaname='app' AND tableowner=current_user)
                FROM pg_roles WHERE rolname=current_user""")
            )
            if unsafe is not False:
                return False
            rows = db.execute(
                text("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='app' AND c.relkind='r'""")
            ).all()
            flags = {r[0]: bool(r[1] and r[2]) for r in rows}
            if not set(REQUIRED_TABLES) <= flags.keys():
                return False
            if not all(flags.get(name) for name in TENANT_TABLES):
                return False
            return bool(
                db.scalar(
                    text("""SELECT
                has_column_privilege(current_user,'app.properties','region_id','UPDATE')
                AND NOT has_column_privilege(
                    current_user,'app.properties','organization_id','UPDATE')
                AND NOT has_table_privilege(
                    current_user,'app.public_accommodation_licenses','INSERT')
                AND EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')""")
                )
            )
    except Exception:
        return False
