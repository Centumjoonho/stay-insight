"""Phase 7 fixtures run only in disposable PostgreSQL databases with runtime RLS."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from test_foundation import onboard, property_body
from test_market import FixtureProvider

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.providers.accommodation import OfficialAccommodationProvider
from app.services.public_sync import synchronize

pytest_plugins = ["test_foundation"]


def region_ids(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/regions")
    assert response.status_code == 200
    return {r["sigungu_name"]: r["id"] for r in response.json()}


def test_region_reference_auth_and_scope(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        # Authenticated reference lookup works before organization onboarding.
        response = client.get("/api/v1/regions", params={"sido": "부산광역시", "level": "SIGUNGU"})
        assert response.status_code == 200
        assert "no-store" in response.headers["cache-control"]
        assert len(response.json()) == 16
        assert all(
            set(r) == {"id", "sido_name", "sigungu_name", "region_level"} for r in response.json()
        )
        assert client.get("/api/v1/regions?sido=서울특별시").status_code == 422
        assert client.get("/api/v1/regions?level=DONG").status_code == 422
        context.app.dependency_overrides.clear()
        assert client.get("/api/v1/regions").status_code == 401
        assert (
            client.get("/api/v1/regions", headers={"Authorization": "Bearer invalid"}).status_code
            == 401
        )


def test_create_edit_clear_region_and_market_without_admin(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = FixtureProvider().batch
    batch.covered_districts = ["수영구", "해운대구"]
    synchronize(context.db.admin, FixtureProvider(batch))

    def forbidden_fetch(*args: object) -> None:
        raise AssertionError("Property changes must never fetch public data")

    monkeypatch.setattr(OfficialAccommodationProvider, "fetch", forbidden_fetch)
    with context.db.admin.connect() as db:
        runs_before = db.scalar(text("SELECT count(*) FROM app.public_data_sync_runs"))
    with TestClient(context.app) as client:
        regions = region_ids(client)
        headers = {"X-Organization-Id": onboard(client)}
        response = client.post(
            "/api/v1/properties",
            headers=headers,
            json=property_body() | {"region_id": regions["수영구"]},
        )
        assert response.status_code == 201, response.text
        item = response.json()
        path = "/api/v1/properties/" + item["id"]
        market = "/api/v1/market/accommodations?property_id=" + item["id"]
        assert item["region"]["sigungu_name"] == "수영구"
        assert client.get(path, headers=headers).json()["region_id"] == regions["수영구"]
        assert (
            client.get("/api/v1/properties", headers=headers).json()["items"][0]["region"]
            == item["region"]
        )
        initial = client.get(market, headers=headers).json()
        assert initial["metrics"]["open_businesses"] == 1
        assert initial["region"]["assignment_method"] == "EXPLICIT_SELECTION"
        updated = client.patch(path, headers=headers, json={"region_id": regions["해운대구"]})
        assert updated.status_code == 200, updated.text
        assert updated.json()["address"] == item["address"]
        data = client.get(market, headers=headers).json()
        assert data["region"]["scope_name"] == "부산광역시 해운대구"
        assert data["metrics"]["open_businesses"] == 0
        assert data["freshness"] == initial["freshness"]
        changed_address = client.patch(
            path, headers=headers, json={"address": "다른 테스트 주소", "road_address": "도로"}
        )
        assert changed_address.status_code == 200
        assert changed_address.json()["region_id"] == regions["해운대구"]
        assert client.get(market, headers=headers).json()["region"] == data["region"]
        assert (
            client.patch(path, headers=headers, json={"region_id": None}).json()["region"] is None
        )
        missing = client.get(market, headers=headers).json()
        assert missing["reason"] == "PROPERTY_REGION_UNAVAILABLE" and missing["metrics"] is None
        legacy = client.post("/api/v1/properties", headers=headers, json=property_body())
        assert legacy.status_code == 201
        assert legacy.json()["region_id"] is None and legacy.json()["region"] is None
    with context.db.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.public_data_sync_runs")) == runs_before


@pytest.mark.parametrize("region", ["bad-uuid", str(uuid4())])
def test_invalid_region_rejected_atomically(context: SimpleNamespace, region: str) -> None:
    with TestClient(context.app) as client:
        headers = {"X-Organization-Id": onboard(client)}
        assert (
            client.post(
                "/api/v1/properties", headers=headers, json=property_body() | {"region_id": region}
            ).status_code
            == 422
        )
        assert client.get("/api/v1/properties", headers=headers).json()["total"] == 0
        created = client.post("/api/v1/properties", headers=headers, json=property_body()).json()
        path = "/api/v1/properties/" + created["id"]
        assert (
            client.patch(
                path, headers=headers, json={"region_id": region, "name": "should rollback"}
            ).status_code
            == 422
        )
        assert client.get(path, headers=headers).json()["name"] == created["name"]


@pytest.mark.parametrize(
    "sido,district,level",
    [
        ("서울특별시", "강남구", "SIGUNGU"),
        ("부산광역시", "미지원구", "SIGUNGU"),
        ("부산광역시", "테스트동", "DONG"),
    ],
)
def test_backend_rejects_unsupported_reference_rows(
    context: SimpleNamespace,
    sido: str,
    district: str,
    level: str,
) -> None:
    # Existing DB constraint already rejects non-Busan/level rows. Temporarily relax it
    # ONLY in the disposable test database to verify the API is independently defensive.
    rid = uuid4()
    with context.db.admin.begin() as db:
        db.execute(text("ALTER TABLE app.regions DROP CONSTRAINT regions_check"))
        db.execute(
            text(
                "INSERT INTO app.regions(id,sido_name,sigungu_name,region_level) "
                "VALUES (:id,:sido,:district,:level)"
            ),
            {"id": rid, "sido": sido, "district": district, "level": level},
        )
    try:
        with TestClient(context.app) as client:
            assert str(rid) not in region_ids(client).values()
            headers = {"X-Organization-Id": onboard(client)}
            assert (
                client.post(
                    "/api/v1/properties",
                    headers=headers,
                    json=property_body() | {"region_id": str(rid)},
                ).status_code
                == 422
            )
            prop = client.post("/api/v1/properties", headers=headers, json=property_body()).json()
            assert (
                client.patch(
                    "/api/v1/properties/" + prop["id"],
                    headers=headers,
                    json={"region_id": str(rid)},
                ).status_code
                == 422
            )
    finally:
        with context.db.admin.begin() as db:
            db.execute(text("DELETE FROM app.regions WHERE id=:id"), {"id": rid})
            db.execute(
                text(
                    "ALTER TABLE app.regions ADD CONSTRAINT regions_check "
                    "CHECK(sido_name='부산광역시' AND region_level='SIGUNGU')"
                )
            )


def test_region_tenant_isolation_revocation_and_column_grants(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        regions = region_ids(client)
        headers = {"X-Organization-Id": onboard(client)}
        item = client.post(
            "/api/v1/properties",
            headers=headers,
            json=property_body() | {"region_id": regions["수영구"]},
        ).json()
        path = "/api/v1/properties/" + item["id"]
        user2 = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user2)
        other = {"X-Organization-Id": onboard(client)}
        for rid in [regions["해운대구"], str(uuid4()), None]:
            assert client.patch(path, headers=other, json={"region_id": rid}).status_code == 404
            assert client.patch(path, headers=headers, json={"region_id": rid}).status_code == 403
        assert client.get(path, headers=other).status_code == 404
        assert (
            client.get(
                "/api/v1/market/accommodations?property_id=" + item["id"], headers=other
            ).status_code
            == 404
        )
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "INSERT INTO app.organization_members(id,organization_id,user_id,role) "
                    "VALUES (:id,:org,:user,'MEMBER')"
                ),
                {"id": uuid4(), "org": UUID(headers["X-Organization-Id"]), "user": user2},
            )
        assert (
            client.patch(path, headers=headers, json={"region_id": regions["해운대구"]}).status_code
            == 200
        )
        with context.db.admin.begin() as db:
            db.execute(
                text("DELETE FROM app.organization_members WHERE user_id=:user"), {"user": user2}
            )
        assert client.patch(path, headers=headers, json={"region_id": None}).status_code == 403
    with context.db.runtime.begin() as db:
        assert db.execute(text("UPDATE app.properties SET region_id=NULL")).rowcount == 0
        assert not db.scalar(
            text(
                "SELECT has_column_privilege(current_user, 'app.properties', "
                "'organization_id', 'UPDATE')"
            )
        )
    with pytest.raises(ProgrammingError), context.db.runtime.begin() as db:
        db.execute(text("UPDATE app.properties SET region_address=NULL"))
    with pytest.raises(ProgrammingError), context.db.runtime.begin() as db:
        db.execute(text("UPDATE app.regions SET sigungu_name='x'"))
