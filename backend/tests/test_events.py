"""Offline fixtures + synthetic data in isolated PostgreSQL only."""

import json
from dataclasses import replace
from datetime import date, timedelta
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
from app.models.events import TourismEvent
from app.providers import events as api
from app.repositories.events import LOCK_KEY
from app.services.event_sync import synchronize

pytest_plugins = ["test_foundation"]
TODAY = date(2026, 10, 2)


def payload() -> Any:
    return json.loads(
        (Path(__file__).parent / "fixtures/events/festival.json").read_text(encoding="utf-8-sig")
    )


def test_real_wire_and_missing_optional() -> None:
    total, rows = api.parse_page(payload(), 1)
    assert total >= 2 and rows[0].district == "500" and rows[1].district == "410"
    assert rows[0].start_date == date(2026, 1, 1)
    p = payload()
    for r in p["response"]["body"]["items"]["item"]:
        r.pop("addr1")
        r.pop("addr2")
        r.pop("progresstype")
        r["areacode"] = "WRONG_LEGACY"
    assert api.parse_page(p, 1)[1][0].address is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("eventstartdate", "20260230"),
        ("eventenddate", "20200101"),
        ("contentid", ""),
        ("title", " "),
        ("lDongSignguCd", "999"),
        ("lDongRegnCd", "11"),
    ],
)
def test_invalid_required(field: str, value: str) -> None:
    p = payload()
    p["response"]["body"]["items"]["item"][0][field] = value
    with pytest.raises(api.EventError):
        api.parse_page(p, 1)


def test_empty_and_error_fail_closed() -> None:
    for p in [{"error": "SYNTHETIC"}, {"response": {"header": {"resultCode": "20"}}}]:
        with pytest.raises(api.EventError):
            api.parse_page(p, 1)
    p = payload()
    p["response"]["body"].update(totalCount=0, numOfRows=0, items="")
    with pytest.raises(api.EventError, match="EMPTY_CONTRACT_UNVERIFIED"):
        api.parse_page(p, 1)


def test_pagination_and_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = api.OfficialEventProvider("TEST_ONLY")

    def request(start: date, end: date, page: int) -> object:
        p = payload()
        body = p["response"]["body"]
        body.update(totalCount=3, pageNo=page)
        if page == 2:
            body["items"]["item"] = body["items"]["item"][:1]
            body["items"]["item"][0]["contentid"] = "999"
            body["numOfRows"] = 1
        return p

    monkeypatch.setattr(provider, "request", request)
    assert len(provider.fetch(TODAY, TODAY + timedelta(days=30))) == 3
    p = payload()
    p["response"]["body"]["totalCount"] = 2
    p["response"]["body"]["items"]["item"][1]["contentid"] = p["response"]["body"]["items"]["item"][
        0
    ]["contentid"]
    monkeypatch.setattr(provider, "request", lambda *args: p)
    with pytest.raises(api.EventError, match="DUPLICATE"):
        provider.fetch(TODAY, TODAY + timedelta(days=30))
    with pytest.raises(api.EventError, match="WINDOW"):
        provider.fetch(TODAY, TODAY + timedelta(days=211))


class Synthetic:
    def __init__(self) -> None:
        self.rows = [
            api.EventRecord(
                str(i + 1),
                code,
                "TEST ONLY",
                TODAY - timedelta(days=1),
                TODAY + timedelta(days=1),
                None,
                None,
            )
            for i, code in enumerate(api.REGIONS)
        ]
        self.fail = False

    def fetch(self, start: date, end: date) -> list[api.EventRecord]:
        if self.fail:
            raise RuntimeError("PRIVATE_SENTINEL")
        return self.rows


@pytest.fixture(autouse=True)
def clean(database: SimpleNamespace) -> None:
    with database.admin.begin() as db:
        db.execute(text("DELETE FROM app.tourism_events"))
        db.execute(text("DELETE FROM app.public_data_sync_runs WHERE source=:s"), {"s": api.SOURCE})


def test_sync_idempotent_revision_absence_failure(database: SimpleNamespace) -> None:
    p = Synthetic()
    run = synchronize(database.admin, p, today=TODAY)
    assert run.status == "COMPLETED" and run.inserted_count == 16
    assert synchronize(database.admin, p, today=TODAY).unchanged_count == 16
    p.rows = [replace(p.rows[0], title="CORRECTION", end_date=TODAY + timedelta(days=5))]
    assert synchronize(database.admin, p, today=TODAY).updated_count == 1
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_events")) == 16
    p.fail = True
    failed = synchronize(database.admin, p, today=TODAY)
    assert failed.status == "FAILED" and failed.error_summary == "EVENT_SYNC_FAILED"
    with database.admin.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_events")) == 16
        assert (
            db.scalar(
                text("SELECT status FROM app.public_data_sync_runs WHERE id=:id"), {"id": failed.id}
            )
            == "FAILED"
        )


def test_atomic_failure_and_mapping(database: SimpleNamespace) -> None:
    def fail(*args: object) -> None:
        raise RuntimeError("PRIVATE")

    event.listen(TourismEvent, "before_insert", fail)
    try:
        assert synchronize(database.admin, Synthetic(), today=TODAY).status == "FAILED"
    finally:
        event.remove(TourismEvent, "before_insert", fail)
    with database.admin.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_events")) == 0
        db.execute(text("UPDATE app.regions SET sigungu_name='TEST' WHERE sigungu_name='수영구'"))
    try:
        assert (
            synchronize(database.admin, Synthetic(), today=TODAY).error_summary
            == "EVENT_REGION_MAPPING_INVALID"
        )
    finally:
        with database.admin.begin() as db:
            db.execute(
                text("UPDATE app.regions SET sigungu_name='수영구' WHERE sigungu_name='TEST'")
            )


def test_locks_grants_constraints(database: SimpleNamespace) -> None:
    with database.admin.begin() as db:
        for key in ["public-license:MOIS_LODGINGS", "public-visitors:KTO_DATALAB_VISITORS_DAILY"]:
            db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key})
        assert synchronize(database.admin, Synthetic(), today=TODAY).status == "COMPLETED"
    with database.admin.begin() as db:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": LOCK_KEY}
        )
        assert (
            synchronize(database.admin, Synthetic(), today=TODAY).error_summary
            == "EVENT_ALREADY_RUNNING"
        )
    with database.runtime.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM app.tourism_events")) == 16
    for sql in [
        "DELETE FROM app.tourism_events",
        "UPDATE app.tourism_events SET title='BAD'",
        "INSERT INTO app.tourism_events(id) VALUES(gen_random_uuid())",
    ]:
        with pytest.raises(ProgrammingError), database.runtime.begin() as db:
            db.execute(text(sql))
    for table in [
        "reservations",
        "expenses",
        "organizations",
        "organization_members",
        "tourism_events",
    ]:
        with pytest.raises(ProgrammingError), database.admin.begin() as db:
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            db.execute(
                text(
                    ("DELETE FROM " if table == "tourism_events" else "SELECT * FROM ")
                    + "app."
                    + table
                )
            )
    for clause in ["end_date='1900-01-01'", "source_event_id='1'", "source_sigungu_code='999'"]:
        with pytest.raises(IntegrityError), database.admin.begin() as db:
            db.execute(text("UPDATE app.tourism_events SET " + clause))


def test_authorized_api_states_sort_counts_and_limits(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.events.today_seoul", lambda: TODAY)
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        path = "/api/v1/market/events?property_id=" + prop
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
        p = Synthetic()
        p.rows = [r for r in p.rows if r.district == "500"]
        p.rows.append(
            replace(
                p.rows[0],
                source_event_id="999",
                start_date=TODAY + timedelta(days=5),
                end_date=TODAY + timedelta(days=6),
            )
        )
        assert synchronize(context.db.admin, p, today=TODAY).status == "COMPLETED"
        data = client.get(path, headers=headers).json()
        assert [r["temporal_status"] for r in data["events"]] == ["ONGOING", "UPCOMING"]
        assert data["summary"] == {"ongoing_count": 1, "next_30_days_count": 1}
        short = client.get(path + "&limit=1", headers=headers).json()
        assert (
            short["truncated"]
            and short["total_count"] == 2
            and short["summary"]["next_30_days_count"] == 1
        )
        empty = client.get(
            path + "&from_date=2026-11-01&to_date=2026-11-02", headers=headers
        ).json()
        assert empty["available"] and empty["events"] == []
        assert (
            client.get(path + "&from_date=2027-10-01", headers=headers).json()["reason"]
            == "OUTSIDE_COLLECTED_WINDOW"
        )
        for q in [
            "&limit=0",
            "&limit=101",
            "&from_date=2026-10-03&to_date=2026-10-01",
            "&to_date=2027-10-01",
        ]:
            assert client.get(path + q, headers=headers).status_code == 422
        other_user = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other_user)
        other, _ = setup(client)
        assert client.get(path, headers=other).status_code == 404
        # Stable subject for subsequent requests.
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(context.user)
        assert client.get(path, headers=other).status_code == 403
        context.app.dependency_overrides.clear()
        assert client.get(path, headers=headers).status_code == 401


def test_transport_key_and_retry_safety(monkeypatch: pytest.MonkeyPatch) -> None:
    from email.message import Message
    from urllib.error import HTTPError
    from urllib.parse import parse_qs, urlsplit

    class Response:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            return json.dumps(payload()).encode()

    seen: list[str] = []

    class Opener:
        def open(self, request: Any, timeout: int) -> Any:
            seen.append(request.full_url)
            assert timeout == 20
            return Response()

    monkeypatch.setattr(api, "build_opener", lambda *args: Opener())
    api.OfficialEventProvider("TEST%2BONLY%3D").request(TODAY, TODAY, 1)
    query = parse_qs(urlsplit(seen[0]).query)
    assert query["serviceKey"] == ["TEST+ONLY="]
    assert query["lDongRegnCd"] == ["26"] and "areaCode" not in query
    with pytest.raises(api.EventError, match="KEY_REQUIRED"):
        api.OfficialEventProvider("").request(TODAY, TODAY, 1)
    calls: list[int] = []

    class Denied:
        def open(self, request: Any, timeout: int) -> Any:
            calls.append(1)
            raise HTTPError("PRIVATE_URL", 403, "PRIVATE", Message(), None)

    monkeypatch.setattr(api, "build_opener", lambda *args: Denied())
    with pytest.raises(api.EventError, match="^EVENT_HTTP_ERROR$"):
        api.OfficialEventProvider("TEST").request(TODAY, TODAY, 1)
    assert len(calls) == 1


