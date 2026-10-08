"""All inventory queries carry both organization and property predicates."""

from datetime import date
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.foundation import Property
from app.models.inventory import AvailabilityOverride, CapacityPeriod


def lock_property(db: Session, org: UUID, prop: UUID) -> Property | None:
    return db.scalar(
        select(Property)
        .where(Property.organization_id == org, Property.id == prop)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def periods(db: Session, org: UUID, prop: UUID) -> list[CapacityPeriod]:
    return list(
        db.scalars(
            select(CapacityPeriod)
            .where(CapacityPeriod.organization_id == org, CapacityPeriod.property_id == prop)
            .order_by(CapacityPeriod.effective_from, CapacityPeriod.id)
        )
    )


def overrides(
    db: Session, org: UUID, prop: UUID, start: date, end: date
) -> list[AvailabilityOverride]:
    return list(
        db.scalars(
            select(AvailabilityOverride)
            .where(
                AvailabilityOverride.organization_id == org,
                AvailabilityOverride.property_id == prop,
                AvailabilityOverride.date >= start,
                AvailabilityOverride.date <= end,
            )
            .order_by(AvailabilityOverride.date)
        )
    )


def invalid_override_exists(db: Session, org: UUID, prop: UUID, fallback: int) -> bool:
    return bool(
        db.scalar(
            text("""
        SELECT EXISTS(SELECT 1 FROM app.property_availability_overrides a
        LEFT JOIN app.property_capacity_periods c
          ON c.organization_id=:org AND c.property_id=:prop
          AND c.effective_from <= a.date AND (c.effective_to IS NULL OR c.effective_to >= a.date)
        WHERE a.organization_id=:org AND a.property_id=:prop
          AND a.unavailable_units > coalesce(c.inventory_units,:fallback))
    """),
            {"org": org, "prop": prop, "fallback": fallback},
        )
    )


def save(db: Session, item: CapacityPeriod | AvailabilityOverride) -> None:
    db.add(item)
    db.flush()


def remove(db: Session, item: CapacityPeriod | AvailabilityOverride) -> None:
    db.delete(item)
    db.flush()
