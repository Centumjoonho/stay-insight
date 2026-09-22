import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.api.dependencies import tenant
from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.core.config import Settings
from app.db.context import set_context
from app.main import create_app
from app.repositories import foundation as repo


@pytest.fixture(scope="module")
def database() -> Iterator[SimpleNamespace]:
    admin_url = os.environ.get("TEST_DATABASE_URL")
    if not admin_url:
        raise pytest.UsageError("TEST_DATABASE_URL is required for real PostgreSQL tenant tests")
    url = make_url(admin_url)
    suffix = uuid4().hex
    database_name, login = "stay_insight_test_" + suffix, "test_app_" + suffix
    password = uuid4().hex
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    test_admin = url.set(database=database_name).render_as_string(hide_password=False)
    original = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = test_admin
    from app.core.config import get_settings
    from app.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} IN ROLE stay_insight_runtime").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )
        runtime_url = url.set(database=database_name, username=login, password=password)
        runtime = create_engine(runtime_url, pool_size=1, max_overflow=3)
        admin = create_engine(test_admin)
        yield SimpleNamespace(
            runtime=runtime,
            admin=admin,
            url=str(runtime_url),
            factory=sessionmaker(runtime, expire_on_commit=False),
        )
        runtime.dispose()
        admin.dispose()
    finally:
        get_engine().dispose()
        get_engine.cache_clear()
        os.environ["DATABASE_URL"] = original
        get_settings.cache_clear()
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))


@pytest.fixture
def context(database: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setattr(tenant, "get_session_factory", lambda: database.factory)
    user = uuid4()
    app = create_app(Settings())
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user)
    return SimpleNamespace(app=app, user=user, db=database)


def onboard(client: TestClient, name: str = "테스트 사업장") -> str:
    response = client.post("/api/v1/onboarding", json={"organization_name": name})
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def property_body() -> dict[str, object]:
    return {
        "name": "테스트 숙소",
        "address": "부산 테스트 주소",
        "accommodation_type": "HOTEL",
        "inventory_units": 3,
    }


def test_onboarding_owner_idempotency(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        assert client.get("/api/v1/me").json()["memberships"] == []
        org = onboard(client)
        assert onboard(client) == org
        me = client.get("/api/v1/me")
        assert me.json()["user_id"] == str(context.user)
        assert me.json()["memberships"] == [
            {
                "organization_id": org,
                "organization_name": "테스트 사업장",
                "role": "OWNER",
            }
        ]
        assert "no-store" in me.headers["cache-control"]
        assert (
            client.post("/api/v1/onboarding", json={"organization_name": "다른 사업장"}).status_code
            == 409
        )


def test_atomic_onboarding(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    name = str(uuid4())

    def failure(_db: Session, _org: UUID, _user: UUID) -> None:
        raise RuntimeError("simulated membership failure")

    monkeypatch.setattr(repo, "insert_owner", failure)
    with TestClient(context.app) as client, pytest.raises(RuntimeError):
        client.post("/api/v1/onboarding", json={"organization_name": name})
    with context.db.admin.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM app.organizations WHERE name=:name"), {"name": name}
            )
            == 0
        )


def test_concurrent_onboarding(context: SimpleNamespace) -> None:
    def submit() -> str:
        with TestClient(context.app) as client:
            return onboard(client, "동시 요청")

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: submit(), range(2)))
    assert values[0] == values[1]


def test_property_crud_and_tenant_isolation(context: SimpleNamespace) -> None:
    other_user = uuid4()
    other_app = create_app(Settings())
    other_app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other_user)
    with TestClient(context.app) as a, TestClient(other_app) as b:
        org_a, org_b = onboard(a, "사업장 A"), onboard(b, "사업장 B")
        ha, hb = {"X-Organization-Id": org_a}, {"X-Organization-Id": org_b}
        created = a.post("/api/v1/properties", headers=ha, json=property_body())
        assert created.status_code == 201, created.text
        property_id = created.json()["id"]
        path = "/api/v1/properties/" + property_id
        assert created.json()["timezone"] == "Asia/Seoul"
        assert a.get(path, headers=ha).json()["id"] == property_id
        assert a.get("/api/v1/properties", headers=ha).json()["total"] == 1
        updated = a.patch(path, headers=ha, json={"inventory_units": 7, "name": "수정된 숙소"})
        assert updated.status_code == 200
        assert updated.json()["inventory_units"] == 7
        assert b.get(path, headers=hb).status_code == 404
        assert b.patch(path, headers=hb, json={"name": "탈취"}).status_code == 404
        for method in ("get", "patch"):
            result = getattr(b, method)(
                path, headers=ha, **({"json": {"name": "탈취"}} if method == "patch" else {})
            )
            assert result.status_code == 403
        assert b.get("/api/v1/properties", headers=ha).status_code == 403
        assert b.post("/api/v1/properties", headers=ha, json=property_body()).status_code == 403
        assert b.get("/api/v1/properties", headers=hb).json()["items"] == []
        assert a.patch(path, headers=ha, json={"organization_id": org_b}).status_code == 422
        assert a.patch(path, headers=ha, json={"name": None}).status_code == 422
        assert a.patch(path, headers=ha, json={"latitude": 35}).status_code == 422
        assert a.get("/api/v1/properties").status_code == 422
        # MEMBER may manage properties as requested, not just OWNER.
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "INSERT INTO app.organization_members(id,organization_id,user_id,role) "
                    "VALUES (:id,:org,:user,'MEMBER')"
                ),
                {"id": uuid4(), "org": org_a, "user": other_user},
            )
        assert b.post("/api/v1/properties", headers=ha, json=property_body()).status_code == 201
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "DELETE FROM app.organization_members "
                    "WHERE organization_id=:org AND user_id=:user"
                ),
                {"org": org_a, "user": other_user},
            )
        assert b.get(path, headers=ha).status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "숙소"},
        property_body() | {"inventory_units": 0},
        property_body() | {"name": "   "},
        property_body() | {"latitude": 91, "longitude": 129},
        property_body() | {"inventory_units": True},
    ],
)
def test_validation(context: SimpleNamespace, body: dict[str, object]) -> None:
    with TestClient(context.app) as client:
        org = onboard(client)
        assert (
            client.post(
                "/api/v1/properties", headers={"X-Organization-Id": org}, json=body
            ).status_code
            == 422
        )


def test_rls_and_pooled_context_reset(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        org = onboard(client)
        created = client.post(
            "/api/v1/properties", headers={"X-Organization-Id": org}, json=property_body()
        )
        assert created.status_code == 201
    with context.db.factory() as db, db.begin():
        assert db.scalar(text("SELECT count(*) FROM app.properties")) == 0
        set_context(db, "app.user_id", context.user)
        set_context(db, "app.organization_id", UUID(org))
        assert db.scalar(text("SELECT count(*) FROM app.properties")) == 1
    with context.db.factory() as db, db.begin():
        assert db.scalar(text("SELECT count(*) FROM app.properties")) == 0
        set_context(db, "app.user_id", uuid4())
        set_context(db, "app.organization_id", UUID(org))
        assert db.scalar(text("SELECT count(*) FROM app.properties")) == 0
        with pytest.raises(ProgrammingError):
            db.execute(
                text(
                    "INSERT INTO app.properties(id,organization_id,name,address,"
                    "accommodation_type,inventory_units) "
                    "VALUES (:id,:org,'x','x','HOTEL',1)"
                ),
                {"id": uuid4(), "org": org},
            )
    with context.db.factory() as db, db.begin():
        assert db.scalar(text("SELECT count(*) FROM app.properties")) == 0


def test_cannot_join_existing_organization_with_bootstrap_context(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        org = onboard(client)
    with context.db.factory() as db, db.begin():
        attacker = uuid4()
        set_context(db, "app.user_id", attacker)
        set_context(db, "app.new_organization_id", UUID(org))
        with pytest.raises(ProgrammingError):
            db.execute(
                text(
                    "INSERT INTO app.organization_members "
                    "(id,organization_id,user_id,role) VALUES (:id,:org,:user,'OWNER')"
                ),
                {"id": uuid4(), "org": org, "user": attacker},
            )


def test_superuser_connection_is_rejected(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = sessionmaker(context.db.admin)
    monkeypatch.setattr(tenant, "get_session_factory", lambda: factory)
    with TestClient(context.app) as client:
        assert client.get("/api/v1/me").status_code == 503
