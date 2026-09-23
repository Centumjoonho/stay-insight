from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from test_expenses import body
from test_imports import setup, upload

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.core.config import Settings
from app.main import create_app
from app.repositories.dashboard import Aggregate, ChannelAggregate
from app.services import dashboard as service

pytest_plugins = ["test_foundation"]


def test_periods_seoul_partial_completed_and_leap_year() -> None:
    today = date(2026, 9, 23)
    period = service.selected_period(None, today)
    assert period.start_date == date(2026, 9, 1)
    assert period.end_date == today and period.is_partial
    assert service.selected_period("2026-08", today).end_date == date(2026, 8, 31)
    assert service.period_for(date(2024, 2, 1), today, 31).end_date == date(2024, 2, 29)
    assert service.shift_month(date(2026, 1, 1), -1) == date(2025, 12, 1)


@pytest.mark.parametrize(
    "month", ["2026-9", "2026-00", "2026-13", "0000-01", "1900-01", "2026-10", "bad"]
)
def test_invalid_or_future_month(month: str) -> None:
    with pytest.raises(HTTPException) as error:
        service.selected_period(month, date(2026, 9, 23))
    assert error.value.status_code == 422


def test_operational_ratios_zero_denominators_and_relationship() -> None:
    available, occupancy, adr, revpar = service.operational_values(47, Decimal(4700000), 3, 23)
    assert available == 69 and occupancy == Decimal("68.12")
    assert adr == Decimal("100000")
    assert revpar is not None and occupancy is not None and adr is not None
    # API percentages are rounded to two decimal places.
    assert abs(revpar - adr * occupancy / 100) <= adr * Decimal("0.00005") + Decimal("0.01")
    assert service.operational_values(0, Decimal(0), 0, 0) == (0, None, None, None)
    assert service.operational_values(0, Decimal(0), 1, 30) == (30, Decimal(0), None, Decimal(0))


def test_negative_profit_margin_and_quality_flags() -> None:
    period = service.selected_period("2026-09", date(2026, 9, 23))
    data = Aggregate(
        channels=[ChannelAggregate("GENERIC", 1, Decimal(100), Decimal(0), 0, 30, 1, 0)],
        occupied=30,
        allocated=Decimal(100),
        overlapping=1,
        overlapping_unknown=1,
        expenses=[("RENT", "FIXED", Decimal(200), 1)],
    )
    result = service.metrics(period, data, 1)
    assert result.financial.known_operating_profit == -100
    assert result.financial.known_operating_margin == -100
    assert result.operations.occupancy_rate == Decimal("130.43")
    assert {"UNKNOWN_STATUS", "MISSING_CHANNEL_FEE", "OCCUPANCY_OVER_100"} <= {
        warning.code for warning in result.data_quality.warnings
    }
    assert result.channels[0].known_channel_fee is None
    data.channels[0].revenue = Decimal(0)
    zero = service.metrics(period, data, 1)
    assert zero.financial.known_operating_margin is None
    assert zero.channels[0].revenue_share_percent is None
    assert service.metrics(period, Aggregate(), 0).operations.revpar is None


def test_delta_baseline_and_percentage_point_semantics() -> None:
    assert service.delta(120, 100, True).percentage_change == 20
    assert service.delta(120, 0, True).percentage_change is None
    assert service.delta(120, -100, True).percentage_change is None
    assert service.delta(120, 0, False).absolute_delta is None
    points = service.delta(Decimal("78.2"), Decimal("71.0"), True, True)
    assert points.percentage_points == Decimal("7.2") and points.percentage_change is None


CSV = (
    b"id,in,out,gross,fee,guests,status\n"
    b"cross,2026-08-31,2026-09-03,300000,30000,1,CONFIRMED\n"
    b"start,2026-09-01,2026-09-04,300000,30000,1,CONFIRMED\n"
    b"partial,2026-09-22,2026-09-25,300000,,1,CONFIRMED\n"
    b"unknown,2026-09-10,2026-09-12,200000,0,1,UNKNOWN\n"
    b"cancelled,2026-09-05,2026-09-10,900000,90000,1,CANCELLED\n"
    b"future,2026-09-24,2026-09-25,100000,10,1,CONFIRMED\n"
    b"previous,2026-08-01,2026-08-03,200000,20000,1,CONFIRMED\n"
    b"year,2025-09-01,2025-09-02,100000,10000,1,CONFIRMED\n"
)


def test_dashboard_complete_population_comparisons_and_trends(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "today_seoul", lambda: date(2026, 9, 23))
    with TestClient(context.app) as client:
        headers, prop = setup(client)  # inventory_units=3
        assert upload(client, headers, prop, CSV).json()["status"] == "COMPLETED"
        for category, kind, amount, day in [
            ("RENT", "FIXED", "100000", "2026-09-01"),
            ("CLEANING", "VARIABLE", "50000", "2026-09-23"),
            ("RENT", "FIXED", "900000", "2026-09-24"),
            ("RENT", "FIXED", "100000", "2026-08-01"),
        ]:
            assert (
                client.post(
                    "/api/v1/expenses",
                    headers=headers,
                    json=body(
                        prop, category=category, cost_type=kind, amount=amount, expense_date=day
                    ),
                ).status_code
                == 201
            )
        response = client.get(
            "/api/v1/dashboard/summary", headers=headers, params={"property_id": prop}
        )
        assert response.status_code == 200, response.text
        result = response.json()
        financial, operations, quality = (
            result["financial"],
            result["operations"],
            result["data_quality"],
        )
        assert financial == {
            "recognized_gross_revenue": "800000",
            "manual_expense_total": "150000",
            "fixed_expense_total": "100000",
            "variable_expense_total": "50000",
            "known_channel_fee_total": "30000",
            "known_cost_total": "180000",
            "known_operating_profit": "620000",
            "known_operating_margin": "77.50",
        }
        assert operations["reservation_count"] == 3
        assert operations["occupied_room_nights"] == 9
        assert operations["available_room_nights"] == 69
        assert operations["occupancy_rate"] == "13.04"
        assert operations["allocated_operational_revenue"] == "900000.000000"
        assert operations["adr"] == "100000.00"
        assert operations["revpar"] == "13043.48"
        assert operations["average_length_of_stay"] == "2.67"
        assert quality["unknown_status_count"] == 1
        assert quality["cancelled_reservation_count"] == 1
        assert quality["channel_fee_known_count"] == 2 and quality["channel_fee_missing_count"] == 1
        assert result["metadata"]["calculation_version"] == "dashboard-v1"
        assert "adr" in result["metadata"]["estimated_metrics"]
        channel = result["channels"][0]
        assert channel["reservation_count"] == 3 and channel["booked_nights"] == 8
        assert channel["recognized_gross_revenue"] == "800000"
        assert channel["revenue_share_percent"] == "100.00"
        assert channel["channel_fee_missing_count"] == 1
        previous = result["comparisons"]["previous_month"]
        assert previous["period"]["end_date"] == "2026-08-23"
        assert previous["metrics"]["recognized_gross_revenue"]["percentage_change"] == "300.00"
        assert previous["metrics"]["occupancy_rate"]["percentage_points"] == "10.14"
        year = result["comparisons"]["previous_year"]
        assert year["period"]["end_date"] == "2025-09-23"
        assert year["metrics"]["recognized_gross_revenue"]["percentage_change"] == "700.00"
        assert "no-store" in response.headers["cache-control"]
        phase4 = client.get(
            "/api/v1/expenses/summary",
            headers=headers,
            params={"property_id": prop, "from": "2026-09-01", "to": "2026-09-23"},
        ).json()
        assert phase4["channel_fee_total"] == "120000"  # Preserve all-status Phase 4 behavior.
        assert (
            client.get("/api/v1/expenses", headers=headers, params={"property_id": prop}).json()[
                "total"
            ]
            == 4
        )
        full = client.get(
            "/api/v1/dashboard/summary",
            headers=headers,
            params={"property_id": prop, "month": "2026-08"},
        ).json()
        assert full["period"]["end_date"] == "2026-08-31"
        assert full["financial"]["recognized_gross_revenue"] == "500000"
        assert full["operations"]["occupied_room_nights"] == 3
        statements: list[str] = []

        def record(
            _conn: object,
            _cursor: object,
            statement: str,
            _params: object,
            _context: object,
            _many: bool,
        ) -> None:
            if statement.startswith("WITH periods"):
                statements.append(statement)

        event.listen(context.db.runtime, "before_cursor_execute", record)
        try:
            for months in (1, 24):
                statements.clear()
                trend = client.get(
                    "/api/v1/dashboard/trends",
                    headers=headers,
                    params={"property_id": prop, "months": months},
                ).json()
                assert len(trend["items"]) == months and len(statements) == 3
                assert trend["items"][-1]["known_operating_profit"] == "620000"
                assert trend["items"][-1]["end_date"] == "2026-09-23"
            zero = trend["items"][0]
            assert zero["recognized_gross_revenue"] == "0"
            assert zero["has_financial_reservations"] is False
        finally:
            event.remove(context.db.runtime, "before_cursor_execute", record)


def test_no_data_expenses_only_and_unknown_fee(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "today_seoul", lambda: date(2026, 9, 23))
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        query = {"property_id": prop}
        empty = client.get("/api/v1/dashboard/summary", headers=headers, params=query).json()
        assert empty["financial"]["known_operating_margin"] is None
        assert (
            empty["operations"]["adr"] is None
            and empty["operations"]["average_length_of_stay"] is None
        )
        assert (
            empty["comparisons"]["previous_month"]["metrics"]["recognized_gross_revenue"][
                "available"
            ]
            is False
        )
        assert client.post("/api/v1/expenses", headers=headers, json=body(prop)).status_code == 201
        expenses = client.get("/api/v1/dashboard/summary", headers=headers, params=query).json()
        assert expenses["financial"]["known_operating_profit"] == "-1200000"
        assert expenses["data_quality"]["has_financial_reservations"] is False
        assert (
            upload(
                client,
                headers,
                prop,
                b"id,in,out,gross,fee,guests,status\nzero,2026-09-01,2026-09-02,0,,1,UNKNOWN\n",
            ).json()["status"]
            == "COMPLETED"
        )
        result = client.get("/api/v1/dashboard/summary", headers=headers, params=query).json()
        assert result["channels"][0]["known_channel_fee"] is None
        assert result["channels"][0]["revenue_share_percent"] is None


def test_dashboard_tenants_revocation_and_validation(context: SimpleNamespace) -> None:
    other_app = create_app(Settings())
    other_app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uuid4())
    # Stable identity for the second organization.
    other_user = uuid4()
    other_app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(other_user)
    with TestClient(context.app) as a, TestClient(other_app) as b:
        ha, pa = setup(a)
        hb, _ = setup(b)
        for endpoint in ("summary", "trends"):
            path = "/api/v1/dashboard/" + endpoint
            assert b.get(path, headers=hb, params={"property_id": pa}).status_code == 404
            assert b.get(path, headers=ha, params={"property_id": pa}).status_code == 403
            assert a.get(path, headers=ha, params={"property_id": str(uuid4())}).status_code == 404
        for count in (0, 25):
            assert (
                a.get(
                    "/api/v1/dashboard/trends",
                    headers=ha,
                    params={"property_id": pa, "months": count},
                ).status_code
                == 422
            )
        assert (
            a.get(
                "/api/v1/dashboard/summary",
                headers=ha,
                params={"property_id": pa, "month": "2026-13"},
            ).status_code
            == 422
        )
        from sqlalchemy import text

        with context.db.admin.begin() as db:
            db.execute(
                text("DELETE FROM app.organization_members WHERE user_id=:user"),
                {"user": context.user},
            )
        for endpoint in ("summary", "trends"):
            assert (
                a.get(
                    "/api/v1/dashboard/" + endpoint, headers=ha, params={"property_id": pa}
                ).status_code
                == 403
            )


def test_dashboard_requires_auth() -> None:
    with TestClient(create_app(Settings())) as client:
        for endpoint in ("summary", "trends"):
            response = client.get(
                "/api/v1/dashboard/" + endpoint, params={"property_id": str(uuid4())}
            )
            assert response.status_code == 401


def test_multiple_channels_keep_unknown_fees_and_exact_shares() -> None:
    result = service.metrics(
        service.selected_period("2026-09", date(2026, 9, 23)),
        Aggregate(
            channels=[
                ChannelAggregate("AIRBNB", 2, Decimal(300), Decimal(20), 1, 4, 0, 0),
                ChannelAggregate("DIRECT", 1, Decimal(100), Decimal(0), 1, 1, 0, 0),
                ChannelAggregate("GENERIC", 1, Decimal(0), Decimal(0), 0, 1, 1, 0),
            ]
        ),
        1,
    )
    assert [c.revenue_share_percent for c in result.channels] == [75, 25, 0]
    assert [c.reservation_count for c in result.channels] == [2, 1, 1]
    assert [c.known_channel_fee for c in result.channels] == [20, 0, None]
    assert result.financial.known_cost_total == 20
    assert result.data_quality.channel_fee_missing_count == 2


def test_fractional_allocation_checkout_boundary_and_single_inventory(
    context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "today_seoul", lambda: date(2026, 9, 23))
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        assert (
            client.patch(
                f"/api/v1/properties/{prop}", headers=headers, json={"inventory_units": 1}
            ).status_code
            == 200
        )
        data = (
            b"id,in,out,gross,fee,guests,status\n"
            b"fraction,2026-08-31,2026-09-03,100,0,1,CONFIRMED\n"
            b"checkout,2026-08-30,2026-09-01,1000,0,1,CONFIRMED\n"
        )
        assert upload(client, headers, prop, data).json()["status"] == "COMPLETED"
        result = client.get(
            "/api/v1/dashboard/summary", headers=headers, params={"property_id": prop}
        ).json()
        assert result["financial"]["recognized_gross_revenue"] == "0"
        ops = result["operations"]
        assert ops["occupied_room_nights"] == 2
        assert ops["available_room_nights"] == 23
        assert ops["allocated_operational_revenue"] == "66.666667"
        assert ops["adr"] == "33.33" and ops["revpar"] == "2.90"
        assert ops["occupancy_rate"] == "8.70"
