"""Synthetic sync/metric data is TEST ONLY; parser uses Phase 9A real captures."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from test_imports import setup

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.models.visitors import VisitorDaily
from app.providers import visitor_api as api
from app.repositories.visitors import LOCK_KEY
from app.services.visitor_sync import synchronize
from app.services.visitors import rolling_metrics

pytest_plugins = ["test_foundation"]
FIXTURES = Path(__file__).parent / "fixtures/tourism_visitors"
TODAY = date(2026, 9, 30)
LATEST = date(2026, 8, 31)


def fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def test_real_parser_filter_empty_error_and_decimal(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = api.OfficialVisitorProvider("TEST_KEY")
    monkeypatch.setattr(provider, "request", lambda day, page: fixture("daily.json"))
    rows = provider.fetch_day(date(2026, 8, 1))
    assert len(rows) == 48
    assert {r.code for r in rows} == set(api.REGIONS)
    assert {r.category for r in rows} == {"1", "2", "3"}
    assert all(isinstance(r.value, Decimal) for r in rows)
    monkeypatch.setattr(provider, "request", lambda day, page: fixture("empty.json"))
    assert provider.fetch_day(date(2026, 9, 1)) == []
    for name in ("missing_parameter.txt",):
        monkeypatch.setattr(provider, "request", lambda day, page, name=name: fixture(name))
        with pytest.raises(api.VisitorError, match="INVALID_RESPONSE"):
            provider.fetch_day(date(2026, 8, 1))
    with pytest.raises(api.VisitorError, match="INVALID_DATE"):
        provider.fetch_day("invalid")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "count", "page", "code", "value", "region", "category", "date", "empty"],
)
def test_rejects_corrupt_wire(mutation: str, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.loads((FIXTURES / "daily.json").read_text())
    body = payload["response"]["body"]
    rows = body["items"]["item"]
    if mutation == "duplicate":
        rows[-1] = rows[0]
    elif mutation == "count":
        body["totalCount"] = 10001
    elif mutation == "page":
        body["pageNo"] = 2
    elif mutation == "code":
        payload["response"]["header"]["resultCode"] = "00"
    elif mutation == "value":
        rows[0]["touNum"] = None
    elif mutation == "region":
        next(r for r in rows if r["signguCode"] == "26350")["signguNm"] = "wrong"
    elif mutation == "category":
        rows[0]["touDivCd"] = "TOTAL"
    elif mutation == "date":
        rows[0]["baseYmd"] = "20260230"
    elif mutation == "empty":
        body["items"]["item"] = []
    provider = api.OfficialVisitorProvider("TEST_KEY")
    monkeypatch.setattr(provider, "request", lambda day, page: payload)
    with pytest.raises(api.VisitorError):
        provider.fetch_day(date(2026, 8, 1))


def test_http_limits_and_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(api.VisitorError, match="KEY_REQUIRED"):
        api.OfficialVisitorProvider("").request(LATEST, 1)
    with pytest.raises(api.VisitorError, match="BUDGET"):
        api.OfficialVisitorProvider("TEST_SECRET", max_requests=0).request(LATEST, 1)

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            return b"x" * size

    class Opener:
        def open(self, request: Any, timeout: int) -> Response:
            from urllib.parse import parse_qs, urlsplit

            assert parse_qs(urlsplit(request.full_url).query)["serviceKey"] == ["TEST+KEY="]
            return Response()

    monkeypatch.setattr(api, "build_opener", lambda *args: Opener())
    with pytest.raises(api.VisitorError, match="RESPONSE_TOO_LARGE"):
        api.OfficialVisitorProvider("TEST%2BKEY%3D").request(LATEST, 1)


class SyntheticProvider:
    def __init__(self) -> None:
        self.omit: set[tuple[str, str, date]] = set()
        self.value = Decimal("123.4567890123456789")
        self.fail = False
        self.calls: list[date] = []

    def fetch_day(self, day: date) -> list[api.VisitorRecord]:
        self.calls.append(day)
        if self.fail:
            raise RuntimeError("TEST_SECRET_MUST_NOT_LOG")
        if day > LATEST:
            return []
        return [
            api.VisitorRecord(
                code,
                name,
                category,
                label,
                day,
                self.value,
                str(day.isoweekday()),
                ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")[
                    day.weekday()
                ],
            )
            for code, name in api.REGIONS.items()
            for category, label in api.CATEGORIES.items()
            if (code, category, day) not in self.omit
        ]


@pytest.fixture(autouse=True)
def clean(database: SimpleNamespace) -> None:
    with database.admin.begin() as db:
        db.execute(text("DELETE FROM app.tourism_visitor_daily"))
        db.execute(
            text("DELETE FROM app.public_data_sync_runs WHERE source=:source"),
            {"source": api.SOURCE},
        )


def test_bootstrap_idempotent_revision_refresh_missing_and_failure(
    database: SimpleNamespace,
) -> None:
    p = SyntheticProvider()
    first = synchronize(database.admin, p, bootstrap=True, today=TODAY)
    assert first.status == "COMPLETED" and first.inserted_count == 120 * 48
    assert first.source_reference_date == LATEST
    assert len(p.calls) == 149
    second = synchronize(database.admin, p, bootstrap=True, today=TODAY)
    assert second.unchanged_count == 5760 and second.inserted_count == 0
    p.value = Decimal("999.1234567890123456789")
    p.omit.add(("26350", "2", LATEST - timedelta(days=1)))
    refreshed = synchronize(database.admin, p, today=TODAY)
    assert refreshed.status == "COMPLETED" and refreshed.updated_count == 35 * 48
    assert (
        refreshed.visitor_coverage
        and refreshed.visitor_coverage["missing_pair_count"] == 29 * 48 + 1
    )
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_visitor_daily")) == 5760
        assert (
            db.scalar(
                text(
                    "SELECT visitor_value FROM app.tourism_visitor_daily "
                    "WHERE source_region_code='26350' AND visitor_category_code='2' "
                    "AND reference_date=:day"
                ),
                {"day": LATEST},
            )
            == p.value
        )
        assert (
            db.scalar(
                text(
                    "SELECT visitor_value FROM app.tourism_visitor_daily "
                    "WHERE source_region_code='26350' AND visitor_category_code='2' "
                    "AND reference_date=:day"
                ),
                {"day": LATEST - timedelta(days=1)},
            )
            is None
        )
        assert db.scalar(
            text(
                "SELECT visitor_value FROM app.tourism_visitor_daily "
                "WHERE source_region_code='26350' AND visitor_category_code='2' "
                "AND reference_date=:day"
            ),
            {"day": LATEST - timedelta(days=40)},
        ) == Decimal("123.4567890123456789")
    p.fail = True
    failed = synchronize(database.admin, p, today=TODAY)
    assert failed.status == "FAILED" and failed.error_summary == "VISITOR_SYNC_FAILED"
    assert failed.inserted_count == 0
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_visitor_daily")) == 5760
        assert (
            db.scalar(
                text("SELECT status FROM app.public_data_sync_runs WHERE id=:id"), {"id": failed.id}
            )
            == "FAILED"
        )


def test_atomic_failure_mapping_and_discovery_bound(database: SimpleNamespace) -> None:
    def fail(*args: object) -> None:
        raise RuntimeError("TEST PRIVATE")

    event.listen(VisitorDaily, "before_insert", fail)
    try:
        run = synchronize(database.admin, SyntheticProvider(), today=TODAY, refresh_days=1)
        assert run.status == "FAILED" and run.inserted_count == 0
    finally:
        event.remove(VisitorDaily, "before_insert", fail)
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_visitor_daily")) == 0
    p = SyntheticProvider()
    run = synchronize(database.admin, p, today=TODAY, lookback=2)
    assert run.error_summary == "VISITOR_NO_DATA_IN_LOOKBACK" and len(p.calls) == 2
    with database.admin.begin() as db:
        db.execute(
            text("UPDATE app.regions SET sigungu_name='TEST_INVALID' WHERE sigungu_name='수영구'")
        )
    try:
        assert (
            synchronize(database.admin, p, today=TODAY).error_summary
            == "VISITOR_REGION_MAPPING_INVALID"
        )
    finally:
        with database.admin.begin() as db:
            db.execute(
                text(
                    "UPDATE app.regions SET sigungu_name='수영구' WHERE sigungu_name='TEST_INVALID'"
                )
            )


def test_lock_independence_and_privileges(database: SimpleNamespace) -> None:
    with database.admin.begin() as db:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": "public-license:MOIS_LODGINGS"},
        )
        assert (
            synchronize(database.admin, SyntheticProvider(), today=TODAY, refresh_days=1).status
            == "COMPLETED"
        )
    with database.admin.begin() as db:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": LOCK_KEY}
        )
        assert (
            synchronize(database.admin, SyntheticProvider(), today=TODAY).error_summary
            == "VISITOR_ALREADY_RUNNING"
        )
    with database.runtime.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_visitor_daily")) == 48
    for query in [
        "DELETE FROM app.tourism_visitor_daily",
        "UPDATE app.tourism_visitor_daily SET visitor_value=0",
        "INSERT INTO app.tourism_visitor_daily(id) VALUES (gen_random_uuid())",
    ]:
        with pytest.raises(ProgrammingError), database.runtime.begin() as db:
            db.execute(text(query))
    for query in [
        "SELECT * FROM app.reservations",
        "SELECT * FROM app.expenses",
        "DELETE FROM app.tourism_visitor_daily",
    ]:
        with pytest.raises(ProgrammingError), database.admin.begin() as db:
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            db.execute(text(query))
    for clause in [
        "visitor_value=-1",
        "visitor_value='NaN'",
        "visitor_category_code='9'",
        "source_region_code='99999'",
    ]:
        with pytest.raises(IntegrityError), database.admin.begin() as db:
            db.execute(text("UPDATE app.tourism_visitor_daily SET " + clause))
    with pytest.raises(IntegrityError), database.admin.begin() as db:
        db.execute(text("UPDATE app.tourism_visitor_daily SET visitor_category_code='1'"))


def test_metric_windows_exact_missing_and_zero() -> None:
    values: dict[date, Decimal | None] = {
        LATEST - timedelta(days=i): Decimal(14 if i < 7 else 7) for i in range(90)
    }
    result = rolling_metrics(values, LATEST)
    assert result.average_7d == 14 and result.previous_7d_average == 7
    assert result.average_28d == Decimal("8.75") and result.change_7d_percent == 100
    del values[LATEST - timedelta(days=2)]
    assert rolling_metrics(values, LATEST).average_7d is None
    assert rolling_metrics(values, LATEST).average_28d is None
    values = {LATEST - timedelta(days=i): Decimal(0) for i in range(28)}
    assert rolling_metrics(values, LATEST).average_7d == 0
    assert rolling_metrics(values, LATEST).change_7d_percent is None


def test_visitor_api_tenant_and_gaps(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        path = "/api/v1/market/visitors?property_id=" + prop
        assert client.get(path, headers=headers).json()["reason"] == "PROPERTY_REGION_UNAVAILABLE"
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "UPDATE app.properties SET region_id=(SELECT id FROM app.regions "
                    "WHERE sigungu_name='수영구') WHERE id=:id"
                ),
                {"id": prop},
            )
        assert client.get(path, headers=headers).json()["reason"] == "NOT_SYNCHRONIZED"
        p = SyntheticProvider()
        p.omit.add(("26500", "2", LATEST - timedelta(days=1)))
        assert synchronize(context.db.admin, p, today=TODAY).status == "COMPLETED"
        data = client.get(path, headers=headers).json()
        assert data["available"] and data["latest"]["date"] == LATEST.isoformat()
        assert data["category"]["code"] == "2" and len(data["categories"]) == 3
        assert len(data["history"]) == 90 and data["history"][-2]["value"] is None
        assert data["rolling"]["average_7d"] is None
        assert (
            client.get(path + "&category=1", headers=headers).json()["rolling"]["average_7d"]
            == "123.46"
        )
        for query in ["&days=121", "&days=0", "&category=TOTAL"]:
            assert client.get(path + query, headers=headers).status_code == 422
        user = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user)
        other, _ = setup(client)
        assert client.get(path, headers=other).status_code == 404
        assert client.get(path, headers=headers).status_code == 403
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "INSERT INTO app.organization_members(id,organization_id,user_id,role) "
                    "VALUES (:id,:org,:user,'MEMBER')"
                ),
                {"id": uuid4(), "org": headers["X-Organization-Id"], "user": user},
            )
        assert client.get(path, headers=headers).status_code == 200
        with context.db.admin.begin() as db:
            db.execute(
                text("DELETE FROM app.organization_members WHERE user_id=:user"), {"user": user}
            )
        assert client.get(path, headers=headers).status_code == 403
        context.app.dependency_overrides.clear()
        assert client.get(path, headers=headers).status_code == 401


def test_multiple_pages_duplicates_and_snapshot_change(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.loads((FIXTURES / "daily.json").read_text())
    all_rows = payload["response"]["body"]["items"]["item"]
    monkeypatch.setattr(api, "PAGE_SIZE", 400)
    calls: list[int] = []

    def request(day: date, page: int) -> object:
        calls.append(page)
        rows = all_rows[(page - 1) * 400 : page * 400]
        return {
            "response": {
                "header": {"resultCode": "0000"},
                "body": {
                    "pageNo": page,
                    "numOfRows": len(rows),
                    "totalCount": 807,
                    "items": {"item": rows},
                },
            }
        }

    provider = api.OfficialVisitorProvider("TEST_ONLY")
    monkeypatch.setattr(provider, "request", request)
    assert len(provider.fetch_day(date(2026, 8, 1))) == 48
    assert calls == [1, 2, 3]
    all_rows[400] = all_rows[0]
    with pytest.raises(api.VisitorError, match="DUPLICATE"):
        provider.fetch_day(date(2026, 8, 1))


def test_cli_safe_config_and_status(
    database: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.jobs import sync_tourism_visitors as job

    monkeypatch.setattr("sys.argv", ["job"])
    monkeypatch.delenv("MARKET_DATABASE_URL", raising=False)
    assert job.main() == 1
    assert "MARKET_DATABASE_URL_REQUIRED" in capsys.readouterr().out
    monkeypatch.setenv("MARKET_DATABASE_URL", "TEST_UNUSED")
    monkeypatch.setattr(job, "create_engine", lambda *a, **kw: database.admin)
    monkeypatch.setattr(job, "OfficialVisitorProvider", lambda *a: SyntheticProvider())
    monkeypatch.setattr(
        job,
        "synchronize",
        lambda engine, provider, **kw: synchronize(engine, provider, today=TODAY, refresh_days=1),
    )
    assert job.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETED"


@pytest.mark.parametrize("value", ["20260230", "2026-08-01", "", "20261301", "2026011"])
def test_invalid_dates_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        api.parse_day(value)
