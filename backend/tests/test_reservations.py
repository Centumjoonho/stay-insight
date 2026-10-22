from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imports import CSV, MAPPING, setup, upload

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.db.context import set_context
from app.repositories import reservations as repo

pytest_plugins = ["test_foundation"]
BODY = {
    "channel": "GENERIC",
    "check_in": "2026-09-01",
    "check_out": "2026-09-03",
    "gross_revenue": "300000",
    "channel_fee": "20000",
    "guest_count": 2,
    "room_units": 1,
    "reservation_status": "CONFIRMED",
}


def edit(c: TestClient, h: dict[str, str], rid: str, expected: int, **values: object):  # type: ignore[no-untyped-def]
    return c.patch(
        f"/api/v1/reservations/{rid}",
        headers=h,
        json={"expected_version": expected, "change_reason": "개발 검증", **values},
    )


def test_manual_lifecycle_and_audit(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        r = c.post(f"/api/v1/properties/{p}/reservations", headers=h, json=BODY)
        assert r.status_code == 200, r.text
        row = r.json()
        assert row["origin"] == "MANUAL" and row["version"] == 1
        assert row["external_reservation_id"] is None and row["import_id"] is None
        rid = row["id"]
        for version, values in enumerate(
            [
                {"gross_revenue": "320000", "room_units": 2},
                {"reservation_status": "CANCELLED"},
                {"reservation_status": "CONFIRMED"},
            ],
            1,
        ):
            changed = edit(c, h, rid, version, **cast(dict[str, object], values))
            assert changed.status_code == 200, changed.text
            assert changed.json()["version"] == version + 1
            assert not changed.json()["manual_protected_fields"]
        assert edit(c, h, rid, 1, gross_revenue="1").status_code == 409
        history = c.get(f"/api/v1/reservations/{rid}/history", headers=h).json()
        assert history["total"] == 4
        assert history["items"][0]["after_values"] == {"reservation_status": "CONFIRMED"}
        event = history["items"][2]
        assert event["before_values"] == {"gross_revenue": "300000", "room_units": 1}
        assert event["after_values"] == {"gross_revenue": "320000", "room_units": 2}
        assert event["actor_subject"] == str(context.user) and event["reason"] == "개발 검증"
        assert datetime.fromisoformat(event["created_at"]).utcoffset() == timedelta(0)
        assert c.delete(f"/api/v1/reservations/{rid}", headers=h).status_code == 405
        assert c.get(f"/api/v1/reservations/{rid}/history?limit=101", headers=h).status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"check_out": "2026-09-01"},
        {"gross_revenue": "-1"},
        {"gross_revenue": "NaN"},
        {"gross_revenue": "1.5"},
        {"channel_fee": "400000"},
        {"room_units": 0},
        {"room_units": True},
        {"room_units": 1.5},
        {"guest_count": 0},
        {"reservation_status": "VOIDED"},
        {"origin": "CSV_IMPORT"},
        {"actor_subject": str(uuid4())},
    ],
)
def test_create_invalid(context: SimpleNamespace, changes: dict[str, object]) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        assert (
            c.post(
                f"/api/v1/properties/{p}/reservations", headers=h, json=BODY | changes
            ).status_code
            == 422
        )


def test_csv_field_protection_release_and_version(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        initial = CSV.replace(b"200000", b"300000")
        first = initial.replace(b"nights", b"units").replace(b",999", b",1")
        assert (
            upload(c, h, p, first, mapping=MAPPING | {"room_units": "units"}).json()["status"]
            == "COMPLETED"
        )
        row = c.get("/api/v1/reservations", headers=h).json()["items"][0]
        rid = row["id"]
        assert row["origin"] == "CSV_IMPORT" and row["version"] == 1
        assert row["room_units"] == 1
        assert c.get(f"/api/v1/reservations/{rid}/history", headers=h).json()["total"] == 0
        changed = edit(c, h, rid, 1, room_units=2).json()
        assert changed["manual_protected_fields"] == ["room_units"]
        # Omitted optional room count remains protected; unprotected gross updates.
        result = upload(c, h, p, initial.replace(b"300000", b"320000")).json()
        assert result["status"] == "COMPLETED" and result["protected_fields_count"] == 1
        row = c.get(f"/api/v1/reservations/{rid}", headers=h).json()
        assert row["room_units"] == 2 and row["gross_revenue"] == "320000" and row["version"] == 3
        # Only protected input differs; no false version/audit or lineage mutation.
        with_units = initial.replace(b"nights", b"units").replace(b"300000", b"320000")
        result = upload(c, h, p, with_units, mapping=MAPPING | {"room_units": "units"}).json()
        assert result["status"] == "COMPLETED"
        assert c.get(f"/api/v1/reservations/{rid}", headers=h).json()["version"] == 3
        released = c.post(
            f"/api/v1/reservations/{rid}/release-overrides",
            headers=h,
            json={"expected_version": 3, "change_reason": "CSV로 관리", "fields": ["room_units"]},
        )
        assert released.status_code == 200, released.text
        assert released.json()["room_units"] == 2 and released.json()["version"] == 4
        assert not released.json()["manual_protected_fields"]
        final = upload(c, h, p, initial.replace(b"300000", b"330000")).json()
        assert final["status"] == "COMPLETED"
        row = c.get(f"/api/v1/reservations/{rid}", headers=h).json()
        assert row["room_units"] is None and row["version"] == 5
        events = c.get(f"/api/v1/reservations/{rid}/history", headers=h).json()["items"]
        assert [e["event_type"] for e in events] == [
            "CSV_UPDATE",
            "MANUAL_OVERRIDE_RELEASED",
            "CSV_UPDATE",
            "MANUAL_UPDATE",
        ]
        assert events[0]["reservation_import_id"] == final["id"]
        assert upload(c, h, p, initial.replace(b"300000", b"330000")).json()["duplicate"]


def test_identity_collisions_atomic_csv_and_invalid_merge(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        url = f"/api/v1/properties/{p}/reservations"
        manual = c.post(url, headers=h, json=BODY | {"external_reservation_id": "R1"}).json()
        assert (
            c.post(url, headers=h, json=BODY | {"external_reservation_id": "R1"}).status_code == 409
        )
        failed = upload(
            c, h, p, CSV + b"R2,2026-09-01,2026-09-03,200000,20000,2,CONFIRMED,1\n"
        ).json()
        assert failed["status"] == "FAILED" and "충돌" in failed["error_message"]
        assert c.get("/api/v1/reservations", headers=h).json()["total"] == 1
        assert c.get(f"/api/v1/reservations/{manual['id']}", headers=h).json()["origin"] == "MANUAL"
        upload(c, h, p, CSV.replace(b"R1", b"R3"))
        imported = c.get("/api/v1/reservations", headers=h).json()["items"]
        imported = next(r for r in imported if r["origin"] == "CSV_IMPORT")
        assert (
            c.post(url, headers=h, json=BODY | {"external_reservation_id": "R3"}).status_code == 409
        )
        rid = imported["id"]
        edit(c, h, rid, 1, channel_fee="190000")
        bad = upload(c, h, p, CSV.replace(b"R1", b"R3").replace(b"200000", b"100000")).json()
        assert bad["status"] == "FAILED"
        assert c.get(f"/api/v1/reservations/{rid}", headers=h).json()["gross_revenue"] == "200000"


def test_reason_forgery_noop_and_dashboard(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        upload(c, h, p)
        row = c.get("/api/v1/reservations", headers=h).json()["items"][0]
        rid = row["id"]
        for changes in (
            {"change_reason": " "},
            {"change_reason": "x" * 501},
            {"version": 99},
            {"origin": "MANUAL"},
            {"channel": "DIRECT"},
            {"gross_revenue": None},
        ):
            response = edit(c, h, rid, 1, **changes)
            assert response.status_code == 422
        assert edit(c, h, rid, 1, gross_revenue="200000").json()["version"] == 1
        assert c.get(f"/api/v1/reservations/{rid}/history", headers=h).json()["total"] == 0
        params = {"property_id": p, "month": "2026-09"}
        before = c.get("/api/v1/dashboard-v2/summary", headers=h, params=params).json()
        assert edit(c, h, rid, 1, room_units=2).status_code == 200
        after = c.get("/api/v1/dashboard-v2/summary", headers=h, params=params).json()
        assert (
            after["operations"]["occupied_room_nights"]
            == 2 * before["operations"]["occupied_room_nights"]
        )
        v1 = c.get("/api/v1/dashboard/summary", headers=h, params=params).json()
        assert (
            v1["operations"]["occupied_room_nights"] == before["operations"]["occupied_room_nights"]
        )
        assert edit(c, h, rid, 2, reservation_status="CANCELLED").status_code == 200
        cancelled = c.get("/api/v1/dashboard-v2/summary", headers=h, params=params).json()
        assert cancelled["operations"]["occupied_room_nights"] == 0


def test_parallel_updates_and_csv(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        upload(c, h, p)
        rid = c.get("/api/v1/reservations", headers=h).json()["items"][0]["id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(lambda n: edit(c, h, rid, 1, room_units=n).status_code, [2, 3])
            )
        assert sorted(outcomes) == [200, 409]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(upload, c, h, p, CSV.replace(b"200000", b"320000")),
                pool.submit(edit, c, h, rid, 2, room_units=4),
            ]
            results = [f.result() for f in futures]
        assert results[0].json()["status"] == "COMPLETED"
        assert results[1].status_code in (200, 409)
        row = c.get(f"/api/v1/reservations/{rid}", headers=h).json()
        assert row["gross_revenue"] == "320000" and row["manual_protected_fields"] == ["room_units"]


def test_security(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        rid = c.post(f"/api/v1/properties/{p}/reservations", headers=h, json=BODY).json()["id"]
        original = context.user
        other = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other)
        hb, _ = setup(c)
        for suffix in ("", "/history"):
            assert c.get(f"/api/v1/reservations/{rid}{suffix}", headers=hb).status_code == 404
        assert edit(c, hb, rid, 1, room_units=2).status_code == 404
        assert (
            c.post(f"/api/v1/properties/{p}/reservations", headers=hb, json=BODY).status_code == 404
        )
        assert (
            c.post(
                f"/api/v1/reservations/{rid}/release-overrides",
                headers=hb,
                json={"expected_version": 1, "change_reason": "test", "fields": ["room_units"]},
            ).status_code
            == 404
        )
        with context.db.runtime.begin() as connection:
            assert (
                connection.execute(text("SELECT id FROM app.reservation_audit_events")).all() == []
            )
        for table in ("reservation_audit_events", "reservation_manual_overrides"):
            with context.db.admin.connect() as db:
                assert db.scalar(
                    text(
                        "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class "
                        "WHERE oid=CAST(:t AS regclass)"
                    ),
                    {"t": "app." + table},
                )
                assert not db.scalar(
                    text("SELECT has_table_privilege('stay_insight_ingestion',:t,'SELECT')"),
                    {"t": "app." + table},
                )
            for operation in ("UPDATE", "DELETE") if table.endswith("events") else ("UPDATE",):
                with pytest.raises(DBAPIError), context.db.runtime.begin() as db:
                    sql = (
                        f"{operation} app.{table} SET reason='tamper'"
                        if operation == "UPDATE" and table.endswith("events")
                        else f"DELETE FROM app.{table}"
                    )
                    if table.endswith("overrides"):
                        sql = f"UPDATE app.{table} SET field_name='status'"
                    db.execute(text(sql))
        with context.db.factory() as db, db.begin():
            set_context(db, "app.user_id", original)
            set_context(db, "app.organization_id", UUID(h["X-Organization-Id"]))
            assert repo.history(db, UUID(h["X-Organization-Id"]), UUID(rid), 50, 0)[1] == 1
        with context.db.admin.begin() as db:
            db.execute(
                text("DELETE FROM app.organization_members WHERE organization_id=:o"),
                {"o": h["X-Organization-Id"]},
            )
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(original)
        assert edit(c, h, rid, 1, room_units=2).status_code == 403
        context.app.dependency_overrides.clear()
        assert (
            c.post(f"/api/v1/properties/{p}/reservations", headers=h, json=BODY).status_code == 401
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("check_in", "2026-08-31"),
        ("check_out", "2026-09-04"),
        ("gross_revenue", "310000"),
        ("channel_fee", None),
        ("guest_count", 3),
        ("reservation_status", "CANCELLED"),
        ("room_units", 2),
    ],
)
def test_each_changed_field_only_is_protected(
    context: SimpleNamespace, field: str, value: object
) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        upload(c, h, p)
        row = c.get("/api/v1/reservations", headers=h).json()["items"][0]
        saved = edit(c, h, row["id"], 1, **{field: value}).json()
        assert saved["manual_protected_fields"] == [field]
        released = c.post(
            f"/api/v1/reservations/{row['id']}/release-overrides",
            headers=h,
            json={"expected_version": 2, "change_reason": "release", "fields": [field]},
        )
        assert released.status_code == 200
        assert released.json()[field] == saved[field]
        assert not released.json()["manual_protected_fields"]


def test_audit_failure_rolls_back_values_protections_and_csv(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated audit write failure")

    with TestClient(context.app) as c:
        h, p = setup(c)
        upload(c, h, p)
        row = c.get("/api/v1/reservations", headers=h).json()["items"][0]
        monkeypatch.setattr(repo, "audit", fail)
        with pytest.raises(RuntimeError):
            edit(c, h, row["id"], 1, room_units=2)
        current = c.get(f"/api/v1/reservations/{row['id']}", headers=h).json()
        assert current["version"] == 1 and not current["manual_protected_fields"]
        assert current["room_units"] is None
        assert upload(c, h, p, CSV.replace(b"200000", b"320000")).json()["status"] == "FAILED"
        current = c.get(f"/api/v1/reservations/{row['id']}", headers=h).json()
        assert current["gross_revenue"] == "200000" and current["version"] == 1
        assert c.get(f"/api/v1/reservations/{row['id']}/history", headers=h).json()["total"] == 0


def test_manual_null_counts_and_actor_policy(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        body = BODY | {"room_units": None, "guest_count": None, "channel_fee": None}
        rows = [
            c.post(f"/api/v1/properties/{p}/reservations", headers=h, json=body).json()
            for _ in range(2)
        ]
        assert rows[0]["id"] != rows[1]["id"]
        assert rows[0]["external_reservation_id"] is None and rows[0]["room_units"] is None
        with pytest.raises(DBAPIError), context.db.factory() as db, db.begin():
            set_context(db, "app.user_id", context.user)
            set_context(db, "app.organization_id", UUID(h["X-Organization-Id"]))
            db.execute(
                text("""INSERT INTO app.reservation_audit_events
                (id,organization_id,property_id,reservation_id,event_type,change_source,
                 actor_subject,changed_fields,before_values,after_values)
                VALUES (:id,:org,:prop,:res,'MANUAL_CREATE','MANUAL',:actor,'[]','{}','{}')"""),
                {
                    "id": uuid4(),
                    "org": h["X-Organization-Id"],
                    "prop": p,
                    "res": rows[0]["id"],
                    "actor": uuid4(),
                },
            )
