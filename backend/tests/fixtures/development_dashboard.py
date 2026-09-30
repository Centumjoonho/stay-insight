"""DEVELOPMENT FIXTURE ONLY. Explicit local command; never called by application startup."""

import argparse
import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.context import set_context
from app.db.session import get_session_factory
from app.models.foundation import AccommodationType, Property
from app.models.imports import Channel
from app.repositories.regions import supported_regions
from app.schemas.expenses import ExpenseCreate
from app.schemas.foundation import PropertyCreate
from app.schemas.imports import ColumnMapping
from app.services import dashboard, expenses, foundation, imports

NAME = "[개발용 더미] 해운대 6객실 샘플"
ADDRESS = "개발 검증용 가상 주소 · 실제 숙소 아님"
CHANNELS = (Channel.AIRBNB, Channel.BOOKING, Channel.AGODA, Channel.DIRECT)
FIELDS = [
    "external_reservation_id",
    "check_in",
    "check_out",
    "gross_revenue",
    "channel_fee",
    "reservation_status",
]
MAPPING = ColumnMapping(**{key: key for key in FIELDS})


def local_only(settings: Settings) -> None:
    url = make_url(settings.database_url.get_secret_value())
    if (
        settings.app_env != "development"
        or url.host != "db"
        or url.database != "stay_insight"
        or url.username != "stay_insight_app"
    ):
        raise ValueError("Development fixture requires the documented local Compose runtime DB")


def fixture_data() -> tuple[dict[Channel, bytes], list[dict[str, object]]]:
    rows: dict[Channel, list[list[object]]] = {channel: [] for channel in CHANNELS}
    costs: list[dict[str, object]] = []
    for index in range(13):
        year, month = divmod(2025 * 12 + 8 + index, 12)
        month += 1
        first = date(year, month, 1)
        for c, channel in enumerate(CHANNELS):
            rate = 80000 + index * 2000 + c * 15000 + (30000 if month in (7, 8) else 0)
            for slot in range(6):
                start = first.replace(day=2 + slot * 4)
                nights = 1 + (c + slot) % 3
                gross = rate * nights
                fee = gross * (15, 12, 10, 0)[c] // 100
                rows[channel].append(
                    [
                        f"DEMO-{year}-{month:02d}-{channel}-{slot}",
                        start.isoformat(),
                        (start + timedelta(days=nights)).isoformat(),
                        gross,
                        fee,
                        "CONFIRMED",
                    ]
                )
        for category, kind, amount in [
            ("RENT", "FIXED", 1200000),
            ("MANAGEMENT_FEE", "FIXED", 150000),
            ("CLEANING", "VARIABLE", 360000),
            ("LAUNDRY", "VARIABLE", 120000),
            ("ELECTRICITY", "VARIABLE", 180000 + index * 2000),
            ("SUPPLIES", "VARIABLE", 80000),
        ]:
            costs.append(
                {
                    "expense_date": first.replace(day=5).isoformat(),
                    "category": category,
                    "cost_type": kind,
                    "amount": amount,
                    "memo": f"[개발용 더미] {year}-{month:02d} {category}",
                }
            )
    rows[Channel.AIRBNB].extend(
        [
            ["DEMO-CROSS-MONTH", "2026-08-31", "2026-09-03", 300000, 45000, "CONFIRMED"],
            ["DEMO-CANCELLED", "2026-09-15", "2026-09-17", 200000, 0, "CANCELLED"],
        ]
    )
    rows[Channel.BOOKING].append(
        [
            "DEMO-MISSING-FEE",
            "2026-09-20",
            "2026-09-21",
            120000,
            "",
            "UNKNOWN",
        ]
    )
    files: dict[Channel, bytes] = {}
    for channel, data in rows.items():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(FIELDS)
        writer.writerows(data)
        files[channel] = output.getvalue().encode("utf-8")
    return files, costs


def seed(db: Session, user: UUID, org: UUID) -> tuple[UUID, bool]:
    set_context(db, "app.user_id", user)
    foundation.authorize_organization(db, user, org)
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": "development-dashboard-v1:" + str(org)},
    )
    existing = db.scalar(
        select(Property).where(
            Property.organization_id == org,
            Property.name == NAME,
        )
    )
    if existing:
        if existing.address != ADDRESS:
            raise ValueError("Existing property is not the expected development fixture")
        # Never overwrite a user's edits or duplicate expenses on a repeated command.
        return existing.id, False
    region = next(r for r in supported_regions(db) if r.sigungu_name == "해운대구")
    prop = foundation.create_property(
        db,
        org,
        PropertyCreate(
            name=NAME,
            address=ADDRESS,
            accommodation_type=AccommodationType.HOTEL,
            inventory_units=6,
            region_id=region.id,
        ),
    )
    files, costs = fixture_data()
    for channel, content in files.items():
        result = imports.import_csv(
            db,
            org,
            user,
            prop.id,
            channel,
            f"development-dashboard-{channel}.csv",
            content,
            MAPPING,
        )
        if result.status != "COMPLETED":
            raise ValueError("Development fixture import failed; roll back entire seed")
    for cost in costs:
        expenses.create(
            db, org, user, ExpenseCreate.model_validate({**cost, "property_id": prop.id})
        )
    # Independent, fixed arithmetic expectation catches seed/mapping mistakes before commit.
    summary = dashboard.summary(db, org, prop.id, "2026-09")
    if (
        summary.financial.recognized_gross_revenue != Decimal(6192000)
        or summary.financial.known_operating_profit != Decimal(3558640)
        or summary.operations.occupied_room_nights != 51
    ):
        raise ValueError("Development fixture does not match documented September totals")
    return prop.id, True


def main() -> None:
    parser = argparse.ArgumentParser(description="Local development fixture; no real owner data")
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument("--organization-id", type=UUID, required=True)
    args = parser.parse_args()
    local_only(get_settings())
    with get_session_factory()() as db, db.begin():
        unsafe = db.scalar(
            text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
        )
        if unsafe:
            raise ValueError("Use the restricted local runtime role")
        prop, created = seed(db, args.user_id, args.organization_id)
    files, costs = fixture_data()
    directory = Path(__file__).parent / "dashboard-demo"
    directory.mkdir(exist_ok=True)
    for channel, content in files.items():
        (directory / f"development-{channel}.csv").write_bytes(content)
    (directory / "development-expenses.json").write_text(
        json.dumps(costs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "property_id": str(prop),
                "created": created,
                "fixture": "development-dashboard-v1",
                "period": "2025-09..2026-09",
            }
        )
    )


if __name__ == "__main__":
    main()
