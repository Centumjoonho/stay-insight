"""Three aggregate queries for any requested set of periods, never one per month."""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard import Period


@dataclass
class ChannelAggregate:
    channel: str
    count: int
    revenue: Decimal
    fee: Decimal
    fee_count: int
    nights: int
    unknown: int
    cancelled: int


@dataclass
class Aggregate:
    channels: list[ChannelAggregate] = field(default_factory=list)
    occupied: int = 0
    allocated: Decimal = Decimal(0)
    overlapping: int = 0
    overlapping_unknown: int = 0
    expenses: list[tuple[str, str, Decimal, int]] = field(default_factory=list)


PERIODS = """WITH periods AS (
    SELECT * FROM jsonb_to_recordset(CAST(:periods AS jsonb))
    AS p(key text, start_date date, end_date date)
) """


def aggregate(
    db: Session, org: UUID, property_id: UUID, periods: dict[str, Period]
) -> dict[str, Aggregate]:
    params = {
        "org": org,
        "property": property_id,
        "periods": json.dumps(
            [
                {
                    "key": key,
                    "start_date": period.start_date.isoformat(),
                    "end_date": period.end_date.isoformat(),
                }
                for key, period in periods.items()
            ]
        ),
    }
    result = {key: Aggregate() for key in periods}
    rows = db.execute(
        text(
            PERIODS
            + """
        SELECT p.key, r.channel,
            count(*) FILTER (WHERE r.reservation_status <> 'CANCELLED') AS count,
            coalesce(sum(r.gross_revenue)
                FILTER (WHERE r.reservation_status <> 'CANCELLED'),0) AS revenue,
            coalesce(sum(r.channel_fee)
                FILTER (WHERE r.reservation_status <> 'CANCELLED'),0) AS fee,
            count(r.channel_fee) FILTER (WHERE r.reservation_status <> 'CANCELLED') AS fee_count,
            coalesce(sum(r.booked_nights)
                FILTER (WHERE r.reservation_status <> 'CANCELLED'),0) AS nights,
            count(*) FILTER (WHERE r.reservation_status = 'UNKNOWN') AS unknown,
            count(*) FILTER (WHERE r.reservation_status = 'CANCELLED') AS cancelled
        FROM periods p JOIN app.reservations r
          ON r.organization_id=:org AND r.property_id=:property
          AND r.check_in >= p.start_date AND r.check_in <= p.end_date
        GROUP BY p.key,r.channel
    """
        ),
        params,
    ).mappings()
    for row in rows:
        result[row["key"]].channels.append(
            ChannelAggregate(
                channel=row["channel"],
                count=row["count"],
                revenue=row["revenue"],
                fee=row["fee"],
                fee_count=row["fee_count"],
                nights=row["nights"],
                unknown=row["unknown"],
                cancelled=row["cancelled"],
            )
        )
    rows = db.execute(
        text(
            PERIODS
            + """
        SELECT p.key, count(*) AS overlapping,
            count(*) FILTER (WHERE r.reservation_status='UNKNOWN') AS unknown,
            sum(least(r.check_out,p.end_date+1)-greatest(r.check_in,p.start_date)) AS occupied,
            sum(r.gross_revenue *
                (least(r.check_out,p.end_date+1)-greatest(r.check_in,p.start_date))::numeric
                / r.booked_nights) AS allocated
        FROM periods p JOIN app.reservations r
          ON r.organization_id=:org AND r.property_id=:property
          AND r.reservation_status <> 'CANCELLED'
          AND r.check_in <= p.end_date AND r.check_out > p.start_date
        GROUP BY p.key
    """
        ),
        params,
    ).mappings()
    for row in rows:
        target = result[row["key"]]
        target.occupied = row["occupied"]
        target.allocated = row["allocated"]
        target.overlapping = row["overlapping"]
        target.overlapping_unknown = row["unknown"]
    rows = db.execute(
        text(
            PERIODS
            + """
        SELECT p.key,e.category,e.cost_type,sum(e.amount) AS amount,count(*) AS count
        FROM periods p JOIN app.expenses e
          ON e.organization_id=:org AND e.property_id=:property
          AND e.expense_date >= p.start_date AND e.expense_date <= p.end_date
        GROUP BY p.key,e.category,e.cost_type
    """
        ),
        params,
    ).mappings()
    for row in rows:
        result[row["key"]].expenses.append(
            (row["category"], row["cost_type"], row["amount"], row["count"])
        )
    return result
