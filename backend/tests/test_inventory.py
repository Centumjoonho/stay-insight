from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from test_imports import MAPPING, setup, upload

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.db.context import set_context
from app.importers.generic import GenericCsvAdapter, parse_csv
from app.schemas.imports import ColumnMapping
from app.services import dashboard_v2

pytest_plugins = ["test_foundation"]
TABLES = ("property_capacity_periods", "property_availability_overrides")


def capacity(
    start: str = "2026-09-01", end: str | None = "2026-09-30", units: int = 6
) -> dict[str, object]:
    return {"effective_from": start, "effective_to": end, "inventory_units": units}


def excluded(units: int = 1) -> dict[str, object]:
    return {"unavailable_units": units, "reason": "MAINTENANCE", "memo": "test only"}


def csv_units(units: str, identifier: str = "R1") -> bytes:
    return (
        f"id,in,out,gross,fee,guests,status,units\n{identifier},2026-09-01,2026-09-04,100,10,2,CONFIRMED,{units}\n"
    ).encode()


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "bad", "2147483648"])
def test_csv_invalid_units(value: str) -> None:
    _, result = GenericCsvAdapter().normalize(
        parse_csv("test.csv", csv_units(value)), ColumnMapping(**MAPPING, room_units="units")
    )
    assert result.invalid_rows == 1
    assert result.errors[0].field == "room_units"


@pytest.mark.parametrize("value,expected", [("", None), ("2", 2)])
def test_csv_optional_units(value: str, expected: int | None) -> None:
    rows, result = GenericCsvAdapter().normalize(
        parse_csv("test.csv", csv_units(value)), ColumnMapping(**MAPPING, room_units="units")
    )
    assert result.invalid_rows == 0 and rows[0].room_units == expected


def test_import_persistence_replacement_and_v1_frozen(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 9, 10))
    with TestClient(context.app) as c:
        h, p = setup(c)
        r = upload(c, h, p, csv_units("2"), mapping=MAPPING | {"room_units": "units"})
        assert r.json()["status"] == "COMPLETED", r.text
        assert upload(c, h, p, csv_units("2"), mapping=MAPPING | {"room_units": "units"}).json()[
            "duplicate"
        ]
        reservation = c.get("/api/v1/reservations", headers=h, params={"property_id": p}).json()[
            "items"
        ][0]
        assert reservation["room_units"] == 2
        v1 = c.get(
            "/api/v1/dashboard/summary", headers=h, params={"property_id": p, "month": "2026-09"}
        ).json()
        v2 = c.get(
            "/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p, "month": "2026-09"}
        ).json()
        assert v1["metadata"]["calculation_version"] == "dashboard-v1"
        assert v1["operations"]["occupied_room_nights"] == 3
        assert v2["operations"]["occupied_room_nights"] == 6
        assert v1["financial"] == v2["financial"] and v1["channels"] == v2["channels"]
        # Different file, same reservation, omitted optional mapping: whole-row replacement.
        assert upload(c, h, p, csv_units("3")).json()["updated_rows"] == 1
        reservation = c.get("/api/v1/reservations", headers=h, params={"property_id": p}).json()[
            "items"
        ][0]
        assert reservation["room_units"] is None


def test_numeric_acceptance_98_available_6_occupied(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 9, 10))
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        assert c.post(root + "/capacity", headers=h, json=capacity(units=10)).status_code == 200
        for day in ("2026-09-01", "2026-09-02"):
            assert (
                c.post(root + "/availability/" + day, headers=h, json=excluded()).status_code == 200
            )
        assert (
            upload(c, h, p, csv_units("2"), mapping=MAPPING | {"room_units": "units"}).json()[
                "status"
            ]
            == "COMPLETED"
        )
        response = c.get("/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p})
        assert response.status_code == 200, response.text
        result = response.json()
        o = result["operations"]
        assert o["available_room_nights"] == 98 and o["occupied_room_nights"] == 6
        assert Decimal(o["occupancy_rate"]) == Decimal("6.12")
        assert Decimal(o["adr"]) == Decimal("16.67")
        assert Decimal(o["revpar"]) == Decimal("1.02")
        assert Decimal(o["allocated_operational_revenue"]) == 100
        assert result["period"]["end_date"] == "2026-09-10"
        assert result["comparisons"]["previous_month"]["period"]["end_date"] == "2026-08-10"
        assert result["comparisons"]["previous_year"]["period"]["end_date"] == "2025-09-10"
        assert result["data_quality"]["capacity_fallback_days"] == 0
        assert result["data_quality"]["missing_room_units_count"] == 0


def test_history_gaps_changes_cross_month_checkout_and_status(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 10, 8))
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        for value in (
            capacity("2026-09-01", "2026-09-10", 6),
            capacity("2026-09-11", "2026-09-20", 8),
        ):
            assert c.post(root + "/capacity", headers=h, json=value).status_code == 200
        assert (
            c.post(root + "/availability/2026-09-01", headers=h, json=excluded()).status_code == 200
        )
        data = (
            b"id,in,out,gross,fee,guests,status,units\n"
            b"A,2026-08-31,2026-09-03,100,0,1,CONFIRMED,2\n"
            b"B,2026-09-30,2026-10-02,200,0,1,UNKNOWN,\n"
            b"C,2026-09-01,2026-09-03,999,0,1,CANCELLED,10\n"
            b"D,2026-08-31,2026-09-01,100,0,1,CONFIRMED,4\n"
        )
        assert (
            upload(c, h, p, data, mapping=MAPPING | {"room_units": "units"}).json()["status"]
            == "COMPLETED"
        )
        r = c.get(
            "/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p, "month": "2026-09"}
        ).json()
        assert r["operations"]["available_room_nights"] == 60 + 80 + 30 - 1
        assert r["operations"]["occupied_room_nights"] == 5
        assert Decimal(r["operations"]["allocated_operational_revenue"]) == Decimal("166.666667")
        assert r["data_quality"]["missing_room_units_count"] == 1
        assert r["data_quality"]["capacity_fallback_days"] == 10
        assert r["financial"]["recognized_gross_revenue"] == "200"
        trends = c.get(
            "/api/v1/dashboard-v2/trends",
            headers=h,
            params={"property_id": p, "month": "2026-09", "months": 2},
        ).json()
        assert trends["metadata"]["calculation_version"] == "dashboard-v2"
        assert trends["items"][-1]["occupancy_rate"] == r["operations"]["occupancy_rate"]
        assert trends["items"][-1]["data_quality"]["capacity_fallback_days"] == 10


def test_zero_denominator_and_daily_overcapacity_not_clamped(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 9, 1))
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        c.post(root + "/availability/2026-09-01", headers=h, json=excluded(3))
        upload(c, h, p, csv_units("4"), mapping=MAPPING | {"room_units": "units"})
        r = c.get("/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p}).json()
        assert r["operations"]["available_room_nights"] == 0
        assert r["operations"]["occupancy_rate"] is None and r["operations"]["revpar"] is None
        assert r["data_quality"]["overcapacity_days"] == 1
        assert "ZERO_AVAILABILITY" in {w["code"] for w in r["data_quality"]["warnings"]}
        c.delete(root + "/availability/2026-09-01", headers=h)
        r = c.get("/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p}).json()
        assert Decimal(r["operations"]["occupancy_rate"]) == Decimal("133.33")
        monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 9, 30))
        r = c.get("/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p}).json()
        assert Decimal(r["operations"]["occupancy_rate"]) < 100
        assert r["data_quality"]["overcapacity_days"] == 3


def test_mutations_overlap_limits_fallback_and_rollback(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        first = c.post(root + "/capacity", headers=h, json=capacity()).json()
        assert (
            c.post(root + "/capacity", headers=h, json=capacity("2026-09-30", None)).status_code
            == 409
        )
        assert (
            c.post(root + "/capacity", headers=h, json=capacity("2026-10-01", None)).status_code
            == 200
        )
        assert c.post(root + "/capacity", headers=h, json=capacity(units=0)).status_code == 422
        assert (
            c.post(
                root + "/capacity", headers=h, json=capacity("2026-09-03", "2026-09-01")
            ).status_code
            == 422
        )
        assert (
            c.post(root + "/availability/2026-09-03", headers=h, json=excluded(7)).status_code
            == 422
        )
        assert (
            c.post(root + "/availability/2026-09-03", headers=h, json=excluded(-1)).status_code
            == 422
        )
        assert (
            c.post(root + "/availability/2026-09-03", headers=h, json=excluded(6)).status_code
            == 200
        )
        assert (
            c.patch(
                root + "/capacity/" + first["id"], headers=h, json=capacity(units=5)
            ).status_code
            == 409
        )
        assert c.delete(root + "/capacity/" + first["id"], headers=h).status_code == 409
        assert c.get(root + "/capacity", headers=h).json()[0]["inventory_units"] == 6
        assert (
            c.post(root + "/availability/2026-09-03", headers=h, json=excluded(2)).status_code
            == 200
        )
        assert (
            c.patch(
                root + "/capacity/" + first["id"], headers=h, json=capacity(units=4)
            ).status_code
            == 200
        )
        assert c.delete(root + "/capacity/" + first["id"], headers=h).status_code == 204
        # Now fallback=3. Reducing fallback must also validate existing overrides.
        assert c.patch(root, headers=h, json={"inventory_units": 1}).status_code == 409
        assert c.get(root, headers=h).json()["inventory_units"] == 3
        assert (
            c.get(
                root + "/availability",
                headers=h,
                params={"start": "2026-09-01", "end": "2027-10-01"},
            ).status_code
            == 422
        )
        days = c.get(
            root + "/availability", headers=h, params={"start": "2026-09-03", "end": "2026-09-03"}
        ).json()
        assert days[0]["available_units"] == 1
        assert c.delete(root + "/availability/2026-09-03", headers=h).status_code == 204
        assert c.delete(root + "/availability/2026-09-03", headers=h).status_code == 404


def test_concurrent_capacity_and_override_are_serialized(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"

        def change_capacity() -> int:
            return int(c.post(root + "/capacity", headers=h, json=capacity(units=1)).status_code)

        def change_override() -> int:
            return int(
                c.post(root + "/availability/2026-09-01", headers=h, json=excluded(2)).status_code
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(change_capacity)
            b = pool.submit(change_override)
            statuses = [a.result(), b.result()]
        assert statuses in ([200, 422], [409, 200])
        day = c.get(
            root + "/availability", headers=h, params={"start": "2026-09-01", "end": "2026-09-01"}
        ).json()[0]
        assert day["available_units"] >= 0


def test_tenant_rls_grants_constraints_and_revoked_membership(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        saved = c.post(root + "/capacity", headers=h, json=capacity()).json()
        c.post(root + "/availability/2026-09-01", headers=h, json=excluded())
        org = UUID(h["X-Organization-Id"])
        with context.db.runtime.begin() as db:
            for table in TABLES:
                assert db.scalar(text(f"SELECT count(*) FROM app.{table}")) == 0
            set_context(db, "app.user_id", context.user)
            set_context(db, "app.organization_id", org)
            for table in TABLES:
                assert (
                    db.scalar(
                        text(f"SELECT count(*) FROM app.{table} WHERE organization_id=:org"),
                        {"org": org},
                    )
                    == 1
                )
                assert db.scalar(
                    text(
                        "SELECT relrowsecurity AND relforcerowsecurity "
                        "FROM pg_class WHERE oid=to_regclass(:table)"
                    ),
                    {"table": "app." + table},
                )
                for permission in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert not db.scalar(
                        text(
                            "SELECT has_table_privilege("
                            "'stay_insight_ingestion',:table,:permission)"
                        ),
                        {"table": "app." + table, "permission": permission},
                    )
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(
                    text(
                        "INSERT INTO app.property_capacity_periods "
                        "(id,organization_id,property_id,effective_from,inventory_units) "
                        "VALUES(:id,:org,:prop,'2026-09-10',1)"
                    ),
                    {"id": uuid4(), "org": org, "prop": p},
                )
            with pytest.raises(ProgrammingError), db.begin_nested():
                db.execute(
                    text(
                        "UPDATE app.property_capacity_periods SET organization_id=:org WHERE id=:id"
                    ),
                    {"org": uuid4(), "id": saved["id"]},
                )
        # Another authenticated member cannot access the first owner's property even with own org.
        other_user = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other_user)
        other_h, _ = setup(c)
        for suffix in ("/capacity", "/availability?start=2026-09-01&end=2026-09-02"):
            assert c.get(root + suffix, headers=other_h).status_code == 404
        assert (
            c.post(root + "/availability/2026-09-01", headers=other_h, json=excluded()).status_code
            == 404
        )
        assert (
            c.patch(root + "/capacity/" + saved["id"], headers=other_h, json=capacity()).status_code
            == 404
        )
        assert c.delete(root + "/capacity/" + saved["id"], headers=other_h).status_code == 404
        assert c.get(root + "/capacity", headers=h).status_code == 403
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(context.user)
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "DELETE FROM app.organization_members "
                    "WHERE organization_id=:org AND user_id=:user"
                ),
                {"org": org, "user": context.user},
            )
        assert c.get(root + "/capacity", headers=h).status_code == 403


def test_v2_comparisons_use_each_period_capacity(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_v2, "today_seoul", lambda: date(2026, 9, 10))
    with TestClient(context.app) as c:
        h, p = setup(c)
        root = f"/api/v1/properties/{p}"
        for start, end, units in (
            ("2026-09-01", "2026-09-30", 6),
            ("2026-08-01", "2026-08-31", 3),
            ("2025-09-01", "2025-09-30", 2),
        ):
            assert (
                c.post(root + "/capacity", headers=h, json=capacity(start, end, units)).status_code
                == 200
            )
        data = (
            b"id,in,out,gross,fee,guests,status,units\n"
            b"A,2026-09-01,2026-09-04,300,0,1,CONFIRMED,2\n"
            b"B,2026-08-01,2026-08-04,300,0,1,CONFIRMED,2\n"
            b"C,2025-09-01,2025-09-04,300,0,1,CONFIRMED,2\n"
        )
        assert (
            upload(c, h, p, data, mapping=MAPPING | {"room_units": "units"}).json()["status"]
            == "COMPLETED"
        )
        r = c.get("/api/v1/dashboard-v2/summary", headers=h, params={"property_id": p}).json()
        assert r["operations"]["available_room_nights"] == 60
        assert Decimal(r["operations"]["occupancy_rate"]) == 10
        assert (
            Decimal(
                r["comparisons"]["previous_month"]["metrics"]["occupancy_rate"]["percentage_points"]
            )
            == -10
        )
        assert (
            Decimal(
                r["comparisons"]["previous_year"]["metrics"]["occupancy_rate"]["percentage_points"]
            )
            == -20
        )
        assert (
            Decimal(
                r["comparisons"]["previous_month"]["metrics"]["recognized_gross_revenue"][
                    "absolute_delta"
                ]
            )
            == 0
        )
        assert Decimal(r["comparisons"]["previous_month"]["metrics"]["adr"]["absolute_delta"]) == 0


def test_direct_rls_cross_tenant_and_ingestion_denied(context: SimpleNamespace) -> None:
    with TestClient(context.app) as c:
        h, p = setup(c)
        org = UUID(h["X-Organization-Id"])
        root = f"/api/v1/properties/{p}"
        assert c.post(root + "/capacity", headers=h, json=capacity()).status_code == 200
        c.post(root + "/availability/2026-09-01", headers=h, json=excluded())
        other = uuid4()
        context.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other)
        other_h, other_p = setup(c)
        other_org = UUID(other_h["X-Organization-Id"])
        with context.db.runtime.begin() as db:
            set_context(db, "app.user_id", other)
            set_context(db, "app.organization_id", other_org)
            for table in TABLES:
                assert (
                    db.scalar(
                        text(f"SELECT count(*) FROM app.{table} WHERE property_id=:prop"),
                        {"prop": p},
                    )
                    == 0
                )
                assert (
                    db.execute(
                        text(f"DELETE FROM app.{table} WHERE property_id=:prop"), {"prop": p}
                    ).rowcount
                    == 0
                )
            # Explicit organization A identity under B context is denied by RLS.
            with pytest.raises(ProgrammingError), db.begin_nested():
                db.execute(
                    text("""
                    INSERT INTO app.property_availability_overrides
                    (id,organization_id,property_id,date,unavailable_units,reason)
                    VALUES(:id,:org,:prop,'2026-09-03',0,'OTHER')
                """),
                    {"id": uuid4(), "org": org, "prop": p},
                )
            # Even a matching B org cannot reference A's property (composite FK).
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(
                    text("""
                    INSERT INTO app.property_availability_overrides
                    (id,organization_id,property_id,date,unavailable_units,reason)
                    VALUES(:id,:org,:prop,'2026-09-03',0,'OTHER')
                """),
                    {"id": uuid4(), "org": other_org, "prop": p},
                )
        # Pooled connection has no leaked context after transaction.
        with context.db.runtime.begin() as db:
            for table in TABLES:
                assert db.scalar(text(f"SELECT count(*) FROM app.{table}")) == 0
        with context.db.admin.begin() as db:
            db.execute(text("SET LOCAL ROLE stay_insight_ingestion"))
            for table in TABLES:
                with pytest.raises(ProgrammingError), db.begin_nested():
                    db.execute(text(f"SELECT * FROM app.{table}"))
                with pytest.raises(ProgrammingError), db.begin_nested():
                    db.execute(text(f"DELETE FROM app.{table}"))
        # No context / no JWT cannot reach newly introduced routes.
        context.app.dependency_overrides.clear()
        assert c.get(root + "/capacity", headers=h).status_code == 401
        assert (
            c.post(root + "/availability/2026-09-01", headers=h, json=excluded()).status_code == 401
        )
