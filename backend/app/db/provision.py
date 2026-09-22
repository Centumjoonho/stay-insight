"""Explicit local runtime-role provisioning; never executed by the API."""

import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.core.config import get_settings


def main() -> None:
    password = os.environ.get("APP_DB_PASSWORD")
    if not password:
        raise SystemExit("Set APP_DB_PASSWORD for the local stay_insight_app login")
    url = make_url(get_settings().database_url.get_secret_value()).set(drivername="postgresql")
    with psycopg.connect(url.render_as_string(hide_password=False)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'stay_insight_app'")
            if not cursor.fetchone():
                cursor.execute("CREATE ROLE stay_insight_app LOGIN")
            cursor.execute(
                sql.SQL("""ALTER ROLE stay_insight_app WITH LOGIN INHERIT NOSUPERUSER
                NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}""").format(
                    sql.Literal(password)
                )
            )
            cursor.execute("GRANT stay_insight_runtime TO stay_insight_app")
    print("Local restricted runtime login configured.")


if __name__ == "__main__":
    main()
