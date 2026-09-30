from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fixtures.development_dashboard import fixture_data, local_only, seed
from sqlalchemy import text
from test_foundation import onboard

from app.core.config import Settings
from app.services import dashboard

pytest_plugins = ["test_foundation"]


@pytest.mark.parametrize(
    "environment,host,database,user",
    [
        ("production", "db", "stay_insight", "stay_insight_app"),
        ("development", "remote.example", "stay_insight", "stay_insight_app"),
        ("development", "db", "other", "stay_insight_app"),
        ("development", "db", "stay_insight", "postgres"),
    ],
)
def test_fixture_refuses_nonlocal_or_privileged_target(
    environment: str,
    host: str,
    database: str,
    user: str,
) -> None:
    with pytest.raises(ValueError, match="local Compose"):
        local_only(
            Settings.model_validate(
                {
                    "app_env": environment,
                    "database_url": f"postgresql+psycopg://{user}:test@{host}:5432/{database}",
                }
            )
        )


def test_demo_dataset_exact_totals_idempotency_and_authorization(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dashboard, "today_seoul", lambda: date(2026, 9, 30))
    with TestClient(context.app) as client:
        org = UUID(onboard(client))
    with context.db.factory() as db, db.begin():
        prop, created = seed(db, context.user, org)
        assert created
        result = dashboard.summary(db, org, prop, "2026-09")
        assert result.financial.recognized_gross_revenue == Decimal(6192000)
        assert result.financial.known_operating_profit == Decimal(3558640)
        assert result.operations.occupied_room_nights == 51
        assert result.operations.occupancy_rate == Decimal("28.33")
        assert result.operations.adr == Decimal("125333.33")
        assert result.operations.revpar == Decimal("35511.11")
        assert result.data_quality.channel_fee_missing_count == 1
        assert result.data_quality.cancelled_reservation_count == 1
        assert seed(db, context.user, org) == (prop, False)
        for table, count in [("reservations", 315), ("expenses", 78), ("reservation_imports", 4)]:
            assert (
                db.scalar(
                    text(
                        f"SELECT count(*) FROM app.{table} "
                        "WHERE organization_id=:org AND property_id=:prop"
                    ),
                    {"org": org, "prop": prop},
                )
                == count
            )
    with context.db.factory() as db, db.begin(), pytest.raises(HTTPException) as failure:
        seed(db, uuid4(), org)
    assert failure.value.status_code == 403
    files, costs = fixture_data()
    assert len(files) == 4 and len(costs) == 78
