import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from test_imports import setup

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.jobs import sync_accommodation_licenses as job
from app.models.market import PublicAccommodationLicense, PublicDataSyncRun
from app.providers.accommodation import (
    LicenseRecord,
    OfficialAccommodationProvider,
    ProviderBatch,
    ProviderUnavailable,
    normalize_district,
    normalize_status,
    normalize_type,
)
from app.services import market
from app.services.public_sync import synchronize

pytest_plugins = ["test_foundation"]


class FixtureProvider:
    """Test-only internal DTOs. No upstream schema or live provider claim."""

    def __init__(self, batch: ProviderBatch | None = None) -> None:
        rows = json.loads(
            (Path(__file__).parent / "fixtures/development-public-licenses.json").read_text(
                encoding="utf-8"
            )
        )["records"]
        self.batch = batch or ProviderBatch(
            records=rows, covered_districts=["수영구"], closure_dates_supported=True
        )

    def fetch(self) -> ProviderBatch:
        return self.batch


@pytest.fixture(autouse=True)
def clean_public(database: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("PUBLIC_ACCOMMODATION_API_KEY", raising=False)
    with database.admin.begin() as db:
        db.execute(text("DELETE FROM app.public_accommodation_licenses"))
        db.execute(text("DELETE FROM app.public_data_sync_runs"))
    yield


@pytest.mark.parametrize("value", ["", "unknown", "관광호텔", "영업/정상", "폐업", "취소"])
def test_unverified_mappings_never_guess(value: str) -> None:
    assert normalize_type(value) == "OTHER"
    assert normalize_status(value) == "UNKNOWN"


def test_provider_blocked_optional_fields_and_malformed() -> None:
    with pytest.raises(ProviderUnavailable, match="API_KEY_REQUIRED"):
        OfficialAccommodationProvider().fetch()
    record = FixtureProvider().batch.records[0]
    assert record.closure_date is None and record.source_updated_at is None
    with pytest.raises(ValidationError):
        LicenseRecord.model_validate({**record.model_dump(), "source_record_id": " "})
    with pytest.raises(ValidationError):
        LicenseRecord.model_validate({**record.model_dump(), "license_date": "bad"})
    assert normalize_district("수영구") == "수영구"
    with pytest.raises(ValueError):
        normalize_district("수영")


def test_sync_idempotency_updates_absence_and_closure(database: SimpleNamespace) -> None:
    provider = FixtureProvider()
    first = synchronize(database.admin, provider)
    assert first.status == "COMPLETED" and first.inserted_count == 4
    second = synchronize(database.admin, provider)
    assert second.unchanged_count == 4 and second.inserted_count == 0
    provider.batch.records = [
        provider.batch.records[0].model_copy(
            update={
                "normalized_business_status": "CLOSED",
                "source_business_status": "TEST 폐업",
                "closure_date": date(2026, 9, 28),
            }
        )
    ]
    third = synchronize(database.admin, provider)
    assert third.updated_count == 1
    with Session(database.admin) as db:
        assert len(list(db.scalars(select(PublicAccommodationLicense)))) == 4
        row = db.scalar(
            select(PublicAccommodationLicense).where(
                PublicAccommodationLicense.source_record_id == "TEST-OPEN"
            )
        )
        assert row and row.normalized_business_status == "CLOSED"


def test_failure_and_incomplete_batch_preserve_snapshot(database: SimpleNamespace) -> None:
    synchronize(database.admin, FixtureProvider())
    failed = synchronize(database.admin, OfficialAccommodationProvider())
    assert failed.status == "FAILED" and failed.error_summary == "API_KEY_REQUIRED"
    batch = FixtureProvider().batch
    batch.failed_count = 1
    batch.records[0].business_name = "MUST NOT WRITE"
    invalid = synchronize(database.admin, FixtureProvider(batch))
    assert invalid.status == "FAILED" and invalid.failed_count == 1 and invalid.fetched_count == 5
    assert invalid.inserted_count == invalid.updated_count == 0
    with Session(database.admin) as db:
        row = db.scalar(
            select(PublicAccommodationLicense).where(
                PublicAccommodationLicense.source_record_id == "TEST-OPEN"
            )
        )
        assert row and row.business_name == "TEST ONLY 숙소"


def test_database_failure_rolls_back_and_redacts(database: SimpleNamespace) -> None:
    def fail(*args: object) -> None:
        raise RuntimeError("secret provider payload")

    event.listen(PublicAccommodationLicense, "before_insert", fail)
    try:
        run = synchronize(database.admin, FixtureProvider())
    finally:
        event.remove(PublicAccommodationLicense, "before_insert", fail)
    assert run.status == "FAILED" and run.error_summary == "SYNC_FAILED"
    assert run.inserted_count == 0
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.public_accommodation_licenses")) == 0


def associate(context: SimpleNamespace, org: str, prop: str) -> None:
    with context.db.admin.begin() as db:
        db.execute(
            text("""UPDATE app.properties SET
            region_id=(SELECT id FROM app.regions WHERE sigungu_name='수영구'),
            region_address=address, region_road_address=road_address
            WHERE id=:prop AND organization_id=:org"""),
            {"prop": prop, "org": org},
        )


def test_market_metrics_availability_stale_and_boundaries(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(market, "today_seoul", lambda: date(2026, 9, 28))
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        path = "/api/v1/market/accommodations?property_id=" + prop
        assert client.get(path, headers=headers).json()["reason"] == "PROPERTY_REGION_UNAVAILABLE"
        associate(context, headers["X-Organization-Id"], prop)
        assert client.get(path, headers=headers).json()["reason"] == "NOT_SYNCHRONIZED"
        run = synchronize(context.db.admin, FixtureProvider())
        data = client.get(path, headers=headers).json()
        assert (
            data["market_context_available"] and data["region"]["scope_name"] == "부산광역시 수영구"
        )
        assert data["window_start"] == "2025-09-29" and data["window_end"] == "2026-09-28"
        assert data["metrics"] == {
            "open_businesses": 1,
            "new_licenses_12m": 2,
            "closures_12m": 1,
            "type_breakdown": {"GENERAL_ACCOMMODATION": 1},
            "unknown_status_count": 1,
            "missing_license_dates": 0,
            "missing_closure_dates": 0,
        }
        assert data["freshness"]["source"] == "MOIS_LODGINGS"
        assert data["freshness"]["collected_at"] and not data["freshness"]["stale"]
        with Session(context.db.admin) as db, db.begin():
            stored = db.get(PublicDataSyncRun, run.id)
            assert stored
            stored.collected_at = datetime.now(UTC) - timedelta(days=8)
            stored.closure_dates_supported = False
        synchronize(context.db.admin, OfficialAccommodationProvider())
        data = client.get(path, headers=headers).json()
        assert data["freshness"]["stale"] and data["metrics"]["closures_12m"] is None
        assert any("실패" in w for w in data["warnings"])
        assert client.get(path + "&reference_date=2026-09-29", headers=headers).status_code == 422
        assert client.get(path + "&reference_date=bad", headers=headers).status_code == 422
        assert market.window_start(date(2024, 2, 29)) == date(2023, 3, 1)
        assert (
            client.patch(
                "/api/v1/properties/" + prop, headers=headers, json={"address": "changed"}
            ).status_code
            == 200
        )
        assert (
            client.get(path, headers=headers).json()["region"]["scope_name"] == "부산광역시 수영구"
        )


def test_confirmed_empty_coverage_and_unknown_dates(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        associate(context, headers["X-Organization-Id"], prop)
        path = "/api/v1/market/accommodations?property_id=" + prop
        synchronize(
            context.db.admin,
            FixtureProvider(
                ProviderBatch(
                    records=[], covered_districts=["수영구"], closure_dates_supported=True
                )
            ),
        )
        data = client.get(path, headers=headers).json()
        assert data["market_context_available"] and data["metrics"]["open_businesses"] == 0
        batch = FixtureProvider().batch
        batch.records[0].license_date = None
        batch.records[1].closure_date = None
        synchronize(context.db.admin, FixtureProvider(batch))
        data = client.get(path, headers=headers).json()
        assert data["metrics"]["new_licenses_12m"] is None
        assert data["metrics"]["closures_12m"] is None


def test_tenant_membership_revocation_and_runtime_read_only(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        path = "/api/v1/market/accommodations?property_id=" + prop
        assert client.get(path, headers=headers).status_code == 200
        user2 = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user2)
        other_headers, _ = setup(client)
        assert client.get(path, headers=other_headers).status_code == 404
        assert client.get(path, headers=headers).status_code == 403
        with context.db.admin.begin() as db:
            db.execute(
                text("""INSERT INTO app.organization_members
                (id,organization_id,user_id,role) VALUES (:id,:org,:user,'MEMBER')"""),
                {"id": uuid4(), "org": UUID(headers["X-Organization-Id"]), "user": user2},
            )
        assert client.get(path, headers=headers).status_code == 200
        with context.db.admin.begin() as db:
            db.execute(
                text("DELETE FROM app.organization_members WHERE user_id=:user"), {"user": user2}
            )
        assert client.get(path, headers=headers).status_code == 403
        context.app.dependency_overrides.clear()
        assert client.get(path, headers=headers).status_code == 401
    with context.db.runtime.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM app.regions")) == 16
    with pytest.raises(ProgrammingError), context.db.runtime.begin() as db:
        db.execute(text("DELETE FROM app.public_accommodation_licenses"))
    with context.db.runtime.begin() as db:
        # Region UPDATE is granted; forced RLS hides every row without tenant context.
        assert db.execute(text("UPDATE app.properties SET region_id=NULL")).rowcount == 0
    with pytest.raises(ProgrammingError), context.db.runtime.begin() as db:
        db.execute(text("INSERT INTO app.public_data_sync_runs(id) VALUES (:id)"), {"id": uuid4()})
    with context.db.admin.begin() as db:
        db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
        assert db.scalar(text("SELECT count(*) FROM app.regions")) == 16
        with pytest.raises(ProgrammingError):
            db.execute(text("SELECT * FROM app.reservations"))


def test_sync_command_missing_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MARKET_DATABASE_URL", raising=False)
    assert job.main() == 1
    assert "MARKET_DATABASE_URL_REQUIRED" in capsys.readouterr().out


def test_duplicate_and_incomplete_coverage_not_published(database: SimpleNamespace) -> None:
    batch = FixtureProvider().batch
    batch.records.append(batch.records[0])
    assert synchronize(database.admin, FixtureProvider(batch)).status == "FAILED"
    batch.records.pop()
    batch.complete = False
    assert synchronize(database.admin, FixtureProvider(batch)).status == "FAILED"
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.public_accommodation_licenses")) == 0


def test_older_source_refused(database: SimpleNamespace) -> None:
    batch = FixtureProvider().batch
    batch.source_reference_date = date(2025, 2, 1)
    assert synchronize(database.admin, FixtureProvider(batch)).status == "COMPLETED"
    batch.source_reference_date = date(2025, 1, 1)
    assert synchronize(database.admin, FixtureProvider(batch)).error_summary == "OLDER_SOURCE_BATCH"


def test_sync_command_success_and_blocked_exit(
    database: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MARKET_DATABASE_URL", "test-only-unused-by-mocked-engine")
    monkeypatch.setattr(job, "create_engine", lambda *args, **kwargs: database.admin)
    monkeypatch.setattr(job, "OfficialAccommodationProvider", FixtureProvider)
    assert job.main() == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 4
    monkeypatch.setattr(job, "OfficialAccommodationProvider", OfficialAccommodationProvider)
    assert job.main() == 1
    assert json.loads(capsys.readouterr().out)["error"] == "API_KEY_REQUIRED"


def test_timeout_preserves_previous_data(database: SimpleNamespace) -> None:
    class TimeoutProvider:
        def fetch(self) -> ProviderBatch:
            raise TimeoutError("secret query key must not be logged")

    synchronize(database.admin, FixtureProvider())
    failed = synchronize(database.admin, TimeoutProvider())
    assert failed.status == "FAILED" and failed.error_summary == "SYNC_FAILED"
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.public_accommodation_licenses")) == 4


def test_admin_assignment_requires_exact_scope_and_address(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.jobs import assign_property_region as assign

    monkeypatch.setattr(assign, "get_engine", lambda: context.db.admin)
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        address = client.get("/api/v1/properties/" + prop, headers=headers).json()["address"]
        args = [
            "assign",
            "--organization-id",
            headers["X-Organization-Id"],
            "--property-id",
            prop,
            "--district",
            "수영구",
            "--confirmed-address",
            address,
        ]
        monkeypatch.setattr("sys.argv", args)
        assign.main()
        data = client.get(
            "/api/v1/market/accommodations", headers=headers, params={"property_id": prop}
        ).json()
        assert data["region"]["scope_name"] == "부산광역시 수영구"
        assert data["reason"] == "NOT_SYNCHRONIZED"
        args[-1] = "wrong address"
        with pytest.raises(SystemExit, match="mismatch"):
            assign.main()
        args[-1] = address
        args[2] = str(uuid4())
        with pytest.raises(SystemExit, match="mismatch"):
            assign.main()
