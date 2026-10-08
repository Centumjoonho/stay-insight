"""Daily owner inventory and occupied units, batched across bounded dashboard periods."""

import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.dashboard import PERIODS
from app.schemas.dashboard import Period


@dataclass
class InventoryAggregate:
    occupied: int
    available: int
    fallback_days: int
    unrecorded_days: int
    overcapacity_days: int
    missing_room_units: int


def aggregate(
    db: Session, org: UUID, prop: UUID, periods: dict[str, Period], fallback: int
) -> dict[str, InventoryAggregate]:
    rows = db.execute(
        text(
            PERIODS
            + """
        , days AS (
            SELECT p.key, (p.start_date + n)::date AS day
            FROM periods p CROSS JOIN LATERAL generate_series(0,p.end_date-p.start_date) n
        ), daily AS (
            SELECT d.key,d.day,
                coalesce(c.inventory_units,:fallback)-coalesce(a.unavailable_units,0) AS available,
                c.id IS NULL AS fallback, a.id IS NULL AS unrecorded,
                coalesce(r.occupied,0) AS occupied
            FROM days d
            LEFT JOIN app.property_capacity_periods c ON c.organization_id=:org
                AND c.property_id=:prop AND c.effective_from<=d.day
                AND (c.effective_to IS NULL OR c.effective_to>=d.day)
            LEFT JOIN app.property_availability_overrides a ON a.organization_id=:org
                AND a.property_id=:prop AND a.date=d.day
            LEFT JOIN LATERAL (
                SELECT sum(coalesce(room_units,1)::bigint) AS occupied
                FROM app.reservations WHERE organization_id=:org AND property_id=:prop
                    AND reservation_status<>'CANCELLED' AND check_in<=d.day AND check_out>d.day
            ) r ON true
        )
        SELECT d.key,sum(d.occupied) AS occupied,sum(d.available) AS available,
            count(*) FILTER (WHERE d.fallback) AS fallback_days,
            count(*) FILTER (WHERE d.unrecorded) AS unrecorded_days,
            count(*) FILTER (WHERE d.occupied>d.available) AS overcapacity_days,
            (SELECT count(*) FROM app.reservations r JOIN periods p ON p.key=d.key
                WHERE r.organization_id=:org AND r.property_id=:prop
                AND r.reservation_status<>'CANCELLED' AND r.room_units IS NULL
                AND r.check_in<=p.end_date AND r.check_out>p.start_date) AS missing
        FROM daily d GROUP BY d.key
    """
        ),
        {
            "org": org,
            "prop": prop,
            "fallback": fallback,
            "periods": json.dumps(
                [
                    {
                        "key": key,
                        "start_date": p.start_date.isoformat(),
                        "end_date": p.end_date.isoformat(),
                    }
                    for key, p in periods.items()
                ]
            ),
        },
    ).mappings()
    return {
        str(r["key"]): InventoryAggregate(
            *(
                int(r[k])
                for k in (
                    "occupied",
                    "available",
                    "fallback_days",
                    "unrecorded_days",
                    "overcapacity_days",
                    "missing",
                )
            )
        )
        for r in rows
    }
