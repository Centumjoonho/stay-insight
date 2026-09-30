from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import signing  # noqa: F401

from app.api.v1 import ready as ready_route
from app.core.auth import jwt as auth
from app.core.config import Settings
from app.main import create_app
from app.runtime import validate_runtime
from app.services.readiness import ready

pytest_plugins = ["test_foundation"]


def hosted(**changes: object) -> Settings:
    return Settings.model_validate(
        {
            "app_env": "staging",
            "database_url": "postgresql+psycopg://restricted:TEST@db.example:5432/postgres?sslmode=require",
            "supabase_url": "https://auth.example.test",
            "cors_origins": ["https://staging.example.test"],
            "staging_allowed_user_ids": ["00000000-0000-0000-0000-000000000001"],
        }
        | changes
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"supabase_url": ""},
        {"cors_origins": []},
        {"cors_origins": ["http://localhost:3000"]},
        {"staging_allowed_user_ids": []},
        {"database_url": "postgresql+psycopg://u:TEST@db.example:5432/postgres"},
        {"database_url": "postgresql+psycopg://u:TEST@db.example:6543/postgres?sslmode=require"},
    ],
)
def test_hosted_startup_fails_closed(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        validate_runtime(hosted(**changes))


def test_hosted_valid_configuration() -> None:
    validate_runtime(hosted())


def test_staging_requires_allowed_verified_subject(
    signing: SimpleNamespace,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = jwt.encode(
        signing.claims, signing.private, algorithm="RS256", headers={"kid": "test-key"}
    )
    settings = hosted()
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    with pytest.raises(HTTPException) as failure:
        auth.verify_access_token(token)
    assert failure.value.status_code == 403
    settings.staging_allowed_user_ids = [UUID(signing.claims["sub"])]
    assert auth.verify_access_token(token).user_id == UUID(signing.claims["sub"])
    invalid = jwt.encode(
        signing.claims | {"exp": 1}, signing.private, algorithm="RS256", headers={"kid": "test-key"}
    )
    with pytest.raises(HTTPException) as failure:
        auth.verify_access_token(invalid)
    assert failure.value.status_code == 401


def test_readiness_role_schema_and_rls(context: SimpleNamespace) -> None:
    assert ready(context.db.runtime)
    assert not ready(context.db.admin)
    with context.db.admin.begin() as db:
        db.execute(text("ALTER TABLE app.expenses NO FORCE ROW LEVEL SECURITY"))
    try:
        assert not ready(context.db.runtime)
    finally:
        with context.db.admin.begin() as db:
            db.execute(text("ALTER TABLE app.expenses FORCE ROW LEVEL SECURITY"))


def test_readiness_http_safe_and_health_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ready_route, "ready", lambda _: False)
    with TestClient(create_app(Settings())) as client:
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert client.get("/api/v1/health").json() == {"status": "ok"}
    monkeypatch.setattr(ready_route, "ready", lambda _: True)
    with TestClient(create_app(Settings())) as client:
        assert client.get("/api/v1/ready").status_code == 200


def test_safe_error_logging(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    application = create_app(hosted())

    @application.get("/api/v1/failure")
    def fail() -> None:
        raise RuntimeError("SECRET_SENTINEL")

    with TestClient(application) as client:
        response = client.get("/api/v1/failure?secret=SECRET_SENTINEL")
    assert response.status_code == 500
    assert "SECRET_SENTINEL" not in response.text + caplog.text


def test_staging_provision_requires_explicit_private_inputs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from app.db import provision_staging

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "SECRET_SENTINEL")
    assert provision_staging.main() == 1
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("CONFIRM_STAGING_PROVISION", raising=False)
    assert provision_staging.main() == 1
    monkeypatch.setenv("CONFIRM_STAGING_PROVISION", "yes")
    assert provision_staging.main() == 1
    assert "SECRET_SENTINEL" not in capsys.readouterr().out


def test_ingestion_verifier_rejects_runtime_login(context: SimpleNamespace) -> None:
    from app.db.verify_staging import verify_ingestion

    assert not verify_ingestion(context.db.runtime.url.render_as_string(hide_password=False))
