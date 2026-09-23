from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from test_imports import setup, upload

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.core.config import Settings
from app.db.context import set_context
from app.main import create_app

pytest_plugins = ["test_foundation"]


def body(property_id: str, **changes: object) -> dict[str, object]:
    return {
        "property_id": property_id,
        "expense_date": "2026-09-01",
        "category": "RENT",
        "cost_type": "FIXED",
        "amount": "1200000",
        "memo": "9월 월세",
    } | changes


def test_crud_filters_and_exact_money(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        created = client.post("/api/v1/expenses", headers=headers, json=body(prop))
        assert created.status_code == 201, created.text
        item = created.json()
        assert item["source"] == "MANUAL"
        assert item["created_by_user_id"] == str(context.user)
        assert item["amount"] == "1200000"
        assert "no-store" in created.headers["cache-control"]
        path = "/api/v1/expenses/" + item["id"]
        assert client.get(path, headers=headers).json() == item
        for date, category, kind, amount in [
            ("2026-09-30", "CLEANING", "VARIABLE", "9007199254740993"),
            ("2026-10-01", "OTHER", "FIXED", "0"),
        ]:
            assert (
                client.post(
                    "/api/v1/expenses",
                    headers=headers,
                    json=body(
                        prop, expense_date=date, category=category, cost_type=kind, amount=amount
                    ),
                ).status_code
                == 201
            )
        query = {"property_id": prop, "from": "2026-09-01", "to": "2026-09-30"}
        result = client.get("/api/v1/expenses", headers=headers, params=query).json()
        assert result["total"] == 2
        assert result["items"][0]["amount"] == "9007199254740993"
        for field, value in [("category", "RENT"), ("cost_type", "FIXED")]:
            filtered = client.get(
                "/api/v1/expenses", headers=headers, params=query | {field: value}
            ).json()
            assert filtered["total"] == 1
            assert filtered["items"][0]["id"] == item["id"]
        page = client.get(
            "/api/v1/expenses", headers=headers, params=query | {"limit": 1, "offset": 1}
        ).json()
        assert page["total"] == 2 and page["items"][0]["id"] == item["id"]
        updated = client.patch(
            path,
            headers=headers,
            json={
                "amount": "250000",
                "memo": None,
                "category": "MANAGEMENT_FEE",
                "cost_type": "VARIABLE",
                "expense_date": "2026-09-02",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["amount"] == "250000" and updated.json()["memo"] is None
        assert updated.json()["created_at"] == item["created_at"]
        assert updated.json()["updated_at"] >= item["updated_at"]
        assert client.delete(path, headers=headers).status_code == 204
        assert client.get(path, headers=headers).status_code == 404
        assert client.delete(path, headers=headers).status_code == 404
        assert client.get("/api/v1/expenses", headers=headers, params=query).json()["total"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": -1},
        {"amount": "1.1"},
        {"amount": 1.0},
        {"amount": True},
        {"amount": "NaN"},
        {"amount": "Infinity"},
        {"amount": "1000000000000000000"},
        {"category": "OTA_FEE"},
        {"category": "PLATFORM_FEE"},
        {"cost_type": "AUTO"},
        {"memo": "x" * 1001},
        {"expense_date": "2026-02-30"},
        {"organization_id": str(uuid4())},
        {"source": "IMPORT"},
        {"created_by_user_id": str(uuid4())},
        {"property_id": None},
    ],
)
def test_invalid_create(context: SimpleNamespace, changes: dict[str, object]) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        assert (
            client.post(
                "/api/v1/expenses", headers=headers, json=(body(prop) | changes)
            ).status_code
            == 422
        )


def test_missing_property_and_invalid_patch_or_filters(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        request = body(prop)
        request.pop("property_id")
        assert client.post("/api/v1/expenses", headers=headers, json=request).status_code == 422
        assert (
            client.post("/api/v1/expenses", headers=headers, json=body(str(uuid4()))).status_code
            == 404
        )
        item = client.post("/api/v1/expenses", headers=headers, json=body(prop)).json()
        for patch in [
            {},
            {"amount": None},
            {"amount": "-1"},
            {"expense_date": None},
            {"cost_type": None},
            {"category": "OTA_FEE"},
            {"property_id": prop},
            {"organization_id": headers["X-Organization-Id"]},
            {"source": "MANUAL"},
        ]:
            assert (
                client.patch(
                    "/api/v1/expenses/" + item["id"], headers=headers, json=patch
                ).status_code
                == 422
            )
        for filters in [
            {"from": "2026-10-01", "to": "2026-09-01"},
            {"limit": "101"},
            {"limit": "0"},
            {"offset": "-1"},
            {"category": "OTA_FEE"},
            {"cost_type": "X"},
        ]:
            assert (
                client.get(
                    "/api/v1/expenses",
                    headers=headers,
                    params={"property_id": prop, **dict(filters)},
                ).status_code
                == 422
            )
        assert client.get("/api/v1/expenses", headers=headers).status_code == 422
        assert (
            client.get(
                "/api/v1/expenses/summary",
                headers=headers,
                params={"property_id": prop, "from": "2026-10-01", "to": "2026-09-01"},
            ).status_code
            == 422
        )


def test_summary_separates_fees_dates_statuses_and_sources(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        for category, kind, amount in [
            ("RENT", "FIXED", 1200000),
            ("MANAGEMENT_FEE", "FIXED", 250000),
            ("CLEANING", "VARIABLE", 300000),
        ]:
            assert (
                client.post(
                    "/api/v1/expenses",
                    headers=headers,
                    json=body(prop, category=category, cost_type=kind, amount=amount),
                ).status_code
                == 201
            )
        client.post("/api/v1/expenses", headers=headers, json=body(prop, expense_date="2026-10-01"))
        csv = (
            b"id,in,out,gross,fee,guests,status\n"
            b"before,2026-08-31,2026-09-02,100,10,1,CONFIRMED\n"
            b"start,2026-09-01,2026-09-02,100,20,1,CONFIRMED\n"
            b"end,2026-09-30,2026-10-03,100,30,1,CANCELLED\n"
            b"missing,2026-09-15,2026-09-16,100,,1,UNKNOWN\n"
            b"zero,2026-09-15,2026-09-16,100,0,1,UNKNOWN\n"
            b"after,2026-10-01,2026-10-02,100,40,1,CONFIRMED\n"
        )
        assert upload(client, headers, prop, csv).json()["status"] == "COMPLETED"
        query = {"property_id": prop, "from": "2026-09-01", "to": "2026-09-30"}
        response = client.get("/api/v1/expenses/summary", headers=headers, params=query)
        assert response.status_code == 200, response.text
        summary = response.json()
        assert summary["manual_expense_total"] == "1750000"
        assert summary["fixed_expense_total"] == "1450000"
        assert summary["variable_expense_total"] == "300000"
        assert summary["channel_fee_total"] == "50"
        assert summary["known_cost_total"] == "1750050"
        assert summary["reservations_with_fee"] == 3 and summary["reservations_missing_fee"] == 1
        assert (
            summary["channel_fee_source"] == "owner_csv"
            and summary["channel_fee_date_basis"] == "check_in"
        )
        assert {row["category"]: row["amount"] for row in summary["category_breakdown"]} == {
            "RENT": "1200000",
            "MANAGEMENT_FEE": "250000",
            "CLEANING": "300000",
        }
        assert {row["cost_type"]: row["amount"] for row in summary["cost_type_breakdown"]} == {
            "FIXED": "1450000",
            "VARIABLE": "300000",
        }
        assert client.get("/api/v1/expenses", headers=headers, params=query).json()["total"] == 3
        empty = client.get(
            "/api/v1/expenses/summary",
            headers=headers,
            params=query | {"from": "2027-01-01", "to": "2027-01-31"},
        ).json()
        assert Decimal(empty["known_cost_total"]) == 0
        assert empty["category_breakdown"] == []


def test_tenant_isolation_members_and_revocation(context: SimpleNamespace) -> None:
    other_user = uuid4()
    other_app = create_app(Settings())
    other_app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other_user)
    with TestClient(context.app) as a, TestClient(other_app) as b:
        ha, pa = setup(a)
        hb, pb = setup(b)
        expense = a.post("/api/v1/expenses", headers=ha, json=body(pa)).json()
        path = "/api/v1/expenses/" + expense["id"]
        assert b.post("/api/v1/expenses", headers=hb, json=body(pa)).status_code == 404
        assert b.get("/api/v1/expenses", headers=hb, params={"property_id": pa}).status_code == 404
        assert b.get(path, headers=hb).status_code == 404
        assert b.patch(path, headers=hb, json={"amount": "1"}).status_code == 404
        assert b.delete(path, headers=hb).status_code == 404
        assert (
            b.get(
                "/api/v1/expenses/summary",
                headers=hb,
                params={"property_id": pa, "from": "2026-09-01", "to": "2026-09-30"},
            ).status_code
            == 404
        )
        assert (
            b.get("/api/v1/expenses", headers=hb, params={"property_id": pb}).json()["total"] == 0
        )
        assert b.get(path, headers=ha).status_code == 403
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "INSERT INTO"
                    " app.organization_members(id,organization_id,user_id,"
                    "role) VALUES (:id,:org,:user,'MEMBER')"
                ),
                {"id": uuid4(), "org": ha["X-Organization-Id"], "user": other_user},
            )
        assert b.patch(path, headers=ha, json={"amount": "0"}).status_code == 200
        assert b.delete(path, headers=ha).status_code == 204
        new = b.post("/api/v1/expenses", headers=ha, json=body(pa)).json()
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "DELETE FROM app.organization_members WHERE"
                    " user_id=:user AND organization_id=:org"
                ),
                {"user": other_user, "org": ha["X-Organization-Id"]},
            )
        for method in ["get", "delete"]:
            assert (
                getattr(b, method)("/api/v1/expenses/" + new["id"], headers=ha).status_code == 403
            )
        assert (
            b.patch("/api/v1/expenses/" + new["id"], headers=ha, json={"amount": "1"}).status_code
            == 403
        )
        assert b.post("/api/v1/expenses", headers=ha, json=body(pa)).status_code == 403


def test_rls_constraints_and_pool_reset(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        item = client.post("/api/v1/expenses", headers=headers, json=body(prop)).json()
    org = UUID(headers["X-Organization-Id"])
    with context.db.factory() as db, db.begin():
        assert db.scalar(text("SELECT count(*) FROM app.expenses")) == 0
        set_context(db, "app.user_id", context.user)
        set_context(db, "app.organization_id", org)
        assert db.scalar(text("SELECT count(*) FROM app.expenses")) == 1
    with context.db.factory() as db, db.begin():
        assert db.scalar(text("SELECT count(*) FROM app.expenses")) == 0
        set_context(db, "app.user_id", uuid4())
        set_context(db, "app.organization_id", org)
        assert (
            db.scalar(
                text("DELETE FROM app.expenses WHERE id=:id RETURNING id"), {"id": item["id"]}
            )
            is None
        )
        assert (
            db.scalar(
                text("UPDATE app.expenses SET amount=1 WHERE id=:id RETURNING id"),
                {"id": item["id"]},
            )
            is None
        )
        with pytest.raises(ProgrammingError), db.begin_nested():
            db.execute(
                text(
                    "INSERT INTO app.expenses SELECT :id, organization_id,"
                    " property_id, expense_date, category, cost_type,"
                    " amount, memo, source, created_by_user_id, created_at,"
                    " updated_at FROM app.expenses"
                ),
                {"id": uuid4()},
            )
            # Explicit forged insert ensures the RLS WITH CHECK is exercised.
            db.execute(
                text(
                    "INSERT INTO"
                    " app.expenses(id,organization_id,property_id,"
                    "expense_date,category,cost_type,amount,source,"
                    "created_by_user_id) VALUES"
                    " (:id,:org,:prop,'2026-09-01','RENT','FIXED',0,'MANUAL',:user)"
                ),
                {"id": uuid4(), "org": org, "prop": prop, "user": context.user},
            )
    with context.db.factory() as db, db.begin():
        set_context(db, "app.user_id", context.user)
        set_context(db, "app.organization_id", org)
        with pytest.raises(ProgrammingError), db.begin_nested():
            db.execute(
                text("UPDATE app.expenses SET organization_id=:org WHERE id=:id"),
                {"org": uuid4(), "id": item["id"]},
            )
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(text("UPDATE app.expenses SET amount=-1 WHERE id=:id"), {"id": item["id"]})
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text("UPDATE app.expenses SET category='OTA_FEE' WHERE id=:id"), {"id": item["id"]}
            )
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text(
                    "INSERT INTO"
                    " app.expenses(id,organization_id,property_id,"
                    "expense_date,category,cost_type,amount,source,"
                    "created_by_user_id) VALUES"
                    " (:id,:org,:prop,'2026-09-01','RENT','FIXED',0,'MANUAL',:user)"
                ),
                {"id": uuid4(), "org": org, "prop": uuid4(), "user": context.user},
            )


def test_authentication_and_delete_cors() -> None:
    with TestClient(create_app(Settings())) as client:
        assert client.get("/api/v1/expenses").status_code == 401
        assert client.delete("/api/v1/expenses/" + str(uuid4())).status_code == 401
        result = client.options(
            "/api/v1/expenses/" + str(uuid4()),
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "authorization,x-organization-id",
            },
        )
        assert result.status_code == 200
        assert "DELETE" in result.headers["access-control-allow-methods"]


def test_phase4_migration_preserves_foundation_and_reservations(context: SimpleNamespace) -> None:
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    with TestClient(context.app) as client:
        headers, prop = setup(client)
        imported = upload(client, headers, prop).json()
        assert imported["status"] == "COMPLETED"
        before = client.get(
            "/api/v1/reservations", headers=headers, params={"property_id": prop}
        ).json()
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.downgrade(config, "0002_csv_imports")
        assert client.get("/api/v1/properties/" + prop, headers=headers).status_code == 200
        assert (
            client.get("/api/v1/reservations", headers=headers, params={"property_id": prop}).json()
            == before
        )
        command.upgrade(config, "head")
        assert (
            client.get("/api/v1/reservations", headers=headers, params={"property_id": prop}).json()
            == before
        )
        assert client.get("/api/v1/imports/" + imported["id"], headers=headers).status_code == 200
        assert client.post("/api/v1/expenses", headers=headers, json=body(prop)).status_code == 201
