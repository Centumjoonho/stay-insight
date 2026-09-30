"""Explicit provisioning AFTER hosted compatibility gate and Alembic. Never startup."""

import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def main() -> int:
    try:
        if os.environ.get("APP_ENV") != "staging":
            raise ValueError("Staging only")
        if os.environ.get("CONFIRM_STAGING_PROVISION") != "yes":
            raise ValueError("Explicit staging provisioning confirmation required")
        url = make_url(os.environ["MIGRATION_DATABASE_URL"])
        if url.host in {"db", "localhost", "127.0.0.1"} or url.query.get("sslmode") not in {
            "require",
            "verify-ca",
            "verify-full",
        }:
            raise ValueError("Verified hosted TLS connection required")
        passwords = [os.environ["APP_DB_PASSWORD"], os.environ["INGESTION_DB_PASSWORD"]]
        if any(len(p) < 24 for p in passwords) or passwords[0] == passwords[1]:
            raise ValueError("Distinct generated passwords required")
        with psycopg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False)
        ) as connection:
            for login, group, password in zip(
                ("stay_insight_app", "stay_insight_collector"),
                ("stay_insight_runtime", "stay_insight_ingestion"),
                passwords,
                strict=True,
            ):
                # Refuse to overwrite/expand an existing identity. Rotation is a separate action.
                if connection.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (login,)
                ).fetchone():
                    raise ValueError("Login already exists")
                connection.execute(
                    sql.SQL("""CREATE ROLE {} LOGIN INHERIT NOSUPERUSER
                    NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}""").format(
                        sql.Identifier(login), sql.Literal(password)
                    )
                )
                connection.execute(
                    sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(login))
                )
                connection.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(str(url.database)), sql.Identifier(login)
                    )
                )
        print("STAGING_LOGINS_CREATED")
        return 0
    except Exception:
        print("STAGING_PROVISION_FAILED: check gate, migration, role existence and private inputs")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
