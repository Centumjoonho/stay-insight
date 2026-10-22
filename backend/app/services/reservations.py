from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.imports import Reservation
from app.repositories import reservations as repo
from app.reservation_fields import MUTABLE_FIELDS
from app.schemas.imports import ReservationResponse
from app.schemas.reservations import (
    AuditList,
    AuditResponse,
    ManualCreate,
    ManualUpdate,
    ReleaseOverrides,
    ReservationValues,
)
from app.services.foundation import get_property


def response(db: Session, org: UUID, item: Reservation) -> ReservationResponse:
    result = ReservationResponse.model_validate(item)
    return result.model_copy(
        update={
            "manual_protected_fields": repo.protections(db, org, [item.id]).get(item.id, []),
            "source": "owner_manual" if item.origin == "MANUAL" else "owner_csv",
        }
    )


def get(db: Session, org: UUID, item_id: UUID, *, lock: bool = False) -> Reservation:
    from app.repositories.imports import get_reservation

    item = repo.locked(db, org, item_id) if lock else get_reservation(db, org, item_id)
    if item is None:
        raise HTTPException(404, "예약을 찾을 수 없습니다.")
    get_property(db, org, item.property_id)
    return item


def guard(item: Reservation, version: int) -> None:
    if item.version != version:
        raise HTTPException(
            409,
            {
                "code": "RESERVATION_VERSION_CONFLICT",
                "message": "다른 변경이 먼저 저장되었습니다. 최신 내용을 다시 확인해 주세요.",
            },
        )


def apply(item: Reservation, values: ReservationValues) -> None:
    for field, value in values.model_dump().items():
        setattr(item, field, value)
    item.booked_nights = (item.check_out - item.check_in).days
    item.net_revenue = None if item.channel_fee is None else item.gross_revenue - item.channel_fee


def create(
    db: Session, org: UUID, actor: UUID, prop: UUID, body: ManualCreate
) -> ReservationResponse:
    from app.repositories.imports import lock_import

    get_property(db, org, prop)
    lock_import(db, org, prop, body.channel)
    try:
        with db.begin_nested():
            item = Reservation(
                organization_id=org,
                property_id=prop,
                origin="MANUAL",
                version=1,
                channel=body.channel,
                external_reservation_id=body.external_reservation_id,
                import_id=None,
            )
            apply(
                item,
                ReservationValues.model_validate(
                    body.model_dump(exclude={"channel", "external_reservation_id"})
                ),
            )
            db.add(item)
            db.flush()
            repo.audit(
                db,
                item,
                actor,
                "MANUAL_CREATE",
                "MANUAL",
                {},
                repo.snapshot(item),
                list(MUTABLE_FIELDS),
            )
            db.flush()
    except IntegrityError as error:
        raise HTTPException(
            409,
            {
                "code": "RESERVATION_IDENTITY_CONFLICT",
                "message": "같은 채널과 예약번호가 이미 존재합니다.",
            },
        ) from error
    return response(db, org, item)


def update(
    db: Session, org: UUID, actor: UUID, item_id: UUID, body: ManualUpdate
) -> ReservationResponse:
    item = get(db, org, item_id, lock=True)
    guard(item, body.expected_version)
    incoming = body.model_dump(exclude_unset=True, exclude={"expected_version", "change_reason"})
    before = repo.snapshot(item)
    try:
        values = ReservationValues.model_validate({**before, **incoming})
    except ValidationError as error:
        raise HTTPException(422, "날짜·매출·수수료 등 입력 조합을 확인해 주세요.") from error
    changes = [field for field in incoming if getattr(item, field) != getattr(values, field)]
    if changes:
        apply(item, values)
        item.version += 1
        if item.origin == "CSV_IMPORT":
            repo.protect(db, item, changes, actor)
        repo.audit(
            db,
            item,
            actor,
            "STATUS_CHANGE" if "reservation_status" in changes else "MANUAL_UPDATE",
            "MANUAL",
            {f: before[f] for f in changes},
            {f: repo.snapshot(item)[f] for f in changes},
            changes,
            body.change_reason,
        )
        db.flush()
    return response(db, org, item)


def release(
    db: Session, org: UUID, actor: UUID, item_id: UUID, body: ReleaseOverrides
) -> ReservationResponse:
    item = get(db, org, item_id, lock=True)
    guard(item, body.expected_version)
    protected = repo.protections(db, org, [item.id]).get(item.id, [])
    fields = sorted({field.value for field in body.fields} & set(protected))
    if fields:
        repo.release(db, org, item.id, fields)
        item.version += 1
        repo.audit(
            db,
            item,
            actor,
            "MANUAL_OVERRIDE_RELEASED",
            "MANUAL",
            {f: "MANUAL_PROTECTED" for f in fields},
            {f: "CSV_MANAGED" for f in fields},
            fields,
            body.change_reason,
        )
        db.flush()
    return response(db, org, item)


def history(db: Session, org: UUID, item_id: UUID, limit: int, offset: int) -> AuditList:
    get(db, org, item_id)
    items, total = repo.history(db, org, item_id, limit, offset)
    return AuditList(items=[AuditResponse.model_validate(item) for item in items], total=total)
