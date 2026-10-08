from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.foundation import Property
from app.models.inventory import AvailabilityOverride, CapacityPeriod
from app.repositories import inventory as repo
from app.schemas.inventory import (
    AvailabilityDay,
    AvailabilityResponse,
    AvailabilityValues,
    CapacityValues,
)
from app.services.foundation import get_property


def locked_property(db: Session, org: UUID, prop: UUID) -> Property:
    item = repo.lock_property(db, org, prop)
    if item is None:
        raise HTTPException(404, "Property not found")
    return item


def validate_existing_overrides(db: Session, org: UUID, prop: UUID, fallback: int) -> None:
    if repo.invalid_override_exists(db, org, prop, fallback):
        raise HTTPException(
            409,
            "기존 판매 제외 객실 수보다 객실 수를 줄일 수 없습니다. "
            "판매 제외 기록을 먼저 수정해 주세요.",
        )


def list_capacity(db: Session, org: UUID, prop: UUID) -> list[CapacityPeriod]:
    get_property(db, org, prop)
    return repo.periods(db, org, prop)


def save_capacity(
    db: Session, org: UUID, prop: UUID, body: CapacityValues, item_id: UUID | None = None
) -> CapacityPeriod:
    property_item = locked_property(db, org, prop)
    rows = repo.periods(db, org, prop)
    item = next((r for r in rows if r.id == item_id), None)
    if item_id is not None and item is None:
        raise HTTPException(404, "객실 수 이력을 찾을 수 없습니다.")
    if item is None and len(rows) >= 1000:
        raise HTTPException(422, "숙소당 객실 수 이력은 최대 1,000개입니다.")
    for row in rows:
        if (
            row.id != item_id
            and row.effective_from <= (body.effective_to or date.max)
            and (row.effective_to is None or row.effective_to >= body.effective_from)
        ):
            raise HTTPException(
                409, "객실 수 이력의 기간이 겹칩니다. 기존 기간을 먼저 수정해 주세요."
            )
    try:
        with db.begin_nested():
            if item is None:
                item = CapacityPeriod(organization_id=org, property_id=prop, **body.model_dump())
            else:
                for key, value in body.model_dump().items():
                    setattr(item, key, value)
            repo.save(db, item)
            validate_existing_overrides(db, org, prop, property_item.inventory_units)
    except IntegrityError as error:
        raise HTTPException(
            409, "객실 수 이력의 기간이 겹치거나 값이 유효하지 않습니다."
        ) from error
    return item


def delete_capacity(db: Session, org: UUID, prop: UUID, item_id: UUID) -> None:
    property_item = locked_property(db, org, prop)
    item = next((r for r in repo.periods(db, org, prop) if r.id == item_id), None)
    if item is None:
        raise HTTPException(404, "객실 수 이력을 찾을 수 없습니다.")
    with db.begin_nested():
        repo.remove(db, item)
        validate_existing_overrides(db, org, prop, property_item.inventory_units)


def capacity_on(rows: list[CapacityPeriod], day: date, fallback: int) -> tuple[int, bool]:
    for row in rows:
        if row.effective_from <= day and (row.effective_to is None or row.effective_to >= day):
            return row.inventory_units, False
    return fallback, True


def validate_range(start: date, end: date) -> None:
    if start < date(1901, 1, 1) or end > date(9998, 12, 31) or not 0 <= (end - start).days < 366:
        raise HTTPException(422, "1901년 이후 날짜로 최대 366일 범위를 선택해 주세요.")


def availability(
    db: Session, org: UUID, prop: UUID, start: date, end: date
) -> list[AvailabilityDay]:
    validate_range(start, end)
    item = get_property(db, org, prop)
    rows = repo.periods(db, org, prop)
    overrides = {r.date: r for r in repo.overrides(db, org, prop, start, end)}
    result = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        base, fallback = capacity_on(rows, day, item.inventory_units)
        record = overrides.get(day)
        unavailable = record.unavailable_units if record else 0
        result.append(
            AvailabilityDay(
                date=day,
                base_capacity=base,
                unavailable_units=unavailable,
                available_units=base - unavailable,
                capacity_source="estimated_property_default" if fallback else "history",
                override=AvailabilityResponse.model_validate(record) if record else None,
            )
        )
    return result


def save_override(
    db: Session, org: UUID, prop: UUID, day: date, body: AvailabilityValues
) -> AvailabilityOverride:
    validate_range(day, day)
    item = locked_property(db, org, prop)
    base, _ = capacity_on(repo.periods(db, org, prop), day, item.inventory_units)
    if body.unavailable_units > base:
        raise HTTPException(422, "판매 제외 객실 수는 해당 날짜의 객실 수를 초과할 수 없습니다.")
    rows = repo.overrides(db, org, prop, day, day)
    record = (
        rows[0] if rows else AvailabilityOverride(organization_id=org, property_id=prop, date=day)
    )
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    repo.save(db, record)
    return record


def delete_override(db: Session, org: UUID, prop: UUID, day: date) -> None:
    validate_range(day, day)
    locked_property(db, org, prop)
    rows = repo.overrides(db, org, prop, day, day)
    if not rows:
        raise HTTPException(404, "판매 제외 기록을 찾을 수 없습니다.")
    repo.remove(db, rows[0])
