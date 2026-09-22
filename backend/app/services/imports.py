from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.importers.generic import CsvAdapter, CsvDocument, GenericCsvAdapter, parse_csv
from app.models.imports import Channel, ReservationImport
from app.repositories import imports as repo
from app.schemas.imports import (
    ColumnMapping,
    ImportList,
    ImportResponse,
    PreviewResponse,
    ReservationList,
    ReservationResponse,
    ValidationResponse,
)
from app.services.foundation import get_property

adapter: CsvAdapter = GenericCsvAdapter()


def preview(filename: str, data: bytes) -> PreviewResponse:
    document = parse_csv(filename, data)
    return PreviewResponse(
        encoding=document.encoding,
        headers=document.headers,
        rows=document.rows[:10],
        total_rows=len(document.rows),
        warnings=document.warnings,
    )


def mapping_from_json(value: str) -> ColumnMapping:
    try:
        return ColumnMapping.model_validate_json(value)
    except ValidationError as error:
        # Never echo user input in a validation error.
        raise HTTPException(
            422, "예약번호, 체크인, 체크아웃, 총 매출 열 연결이 필요합니다."
        ) from error


def validate(
    db: Session, org: UUID, property_id: UUID, filename: str, data: bytes, mapping: ColumnMapping
) -> ValidationResponse:
    get_property(db, org, property_id)
    _, summary = adapter.normalize(parse_csv(filename, data), mapping)
    return summary


def import_csv(
    db: Session,
    org: UUID,
    user: UUID,
    property_id: UUID,
    channel: Channel,
    filename: str,
    data: bytes,
    mapping: ColumnMapping,
) -> ImportResponse:
    get_property(db, org, property_id)
    document: CsvDocument = parse_csv(filename, data)
    repo.lock_import(db, org, property_id, channel)
    previous = repo.duplicate(db, org, property_id, channel, document.checksum)
    if previous:
        return ImportResponse.model_validate(previous).model_copy(update={"duplicate": True})
    rows, summary = adapter.normalize(document, mapping)
    batch = ReservationImport(
        organization_id=org,
        property_id=property_id,
        channel=channel,
        original_filename=document.filename,
        file_checksum=document.checksum,
        status="PENDING",
        total_rows=summary.total_rows,
        imported_rows=0,
        rejected_rows=summary.invalid_rows,
        inserted_rows=0,
        updated_rows=0,
        created_by_user_id=user,
        column_mapping=mapping.model_dump(exclude_none=True),
        validation_errors=[error.model_dump() for error in summary.errors],
    )
    repo.save_batch(db, batch)
    batch_id = batch.id
    changes: dict[str, object] = {
        "status": "FAILED",
        "completed_at": datetime.now(UTC),
        "imported_rows": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "error_message": "검증 오류로 전체 가져오기가 취소되었습니다.",
    }
    if not summary.invalid_rows:
        try:
            # Roll back ALL reservation changes before recording safe failure metadata.
            with db.begin_nested():
                repo.update_batch(db, org, property_id, batch_id, {"status": "PROCESSING"})
                inserted, updated = repo.upsert_rows(db, batch, rows)
                batch = repo.update_batch(
                    db,
                    org,
                    property_id,
                    batch.id,
                    {
                        "status": "COMPLETED",
                        "inserted_rows": inserted,
                        "updated_rows": updated,
                        "imported_rows": len(rows),
                        "completed_at": datetime.now(UTC),
                    },
                )
        except Exception:
            # Driver exception parameters can include raw values; never log them.
            changes["error_message"] = "예약 변경을 취소했습니다. 다시 시도해 주세요."
        else:
            return ImportResponse.model_validate(batch)
    batch = repo.update_batch(db, org, property_id, batch_id, changes)
    return ImportResponse.model_validate(batch)


def import_detail(db: Session, org: UUID, item_id: UUID) -> ImportResponse:
    item = repo.get_import(db, org, item_id)
    if item is None:
        raise HTTPException(404, "가져오기 기록을 찾을 수 없습니다.")
    return ImportResponse.model_validate(item)


def import_list(
    db: Session,
    org: UUID,
    property_id: UUID | None,
    channel: Channel | None,
    limit: int,
    offset: int,
) -> ImportList:
    if property_id:
        get_property(db, org, property_id)
    items, total = repo.list_imports(db, org, property_id, channel, limit, offset)
    return ImportList(items=[ImportResponse.model_validate(item) for item in items], total=total)


def reservation_detail(db: Session, org: UUID, item_id: UUID) -> ReservationResponse:
    item = repo.get_reservation(db, org, item_id)
    if item is None:
        raise HTTPException(404, "예약을 찾을 수 없습니다.")
    return ReservationResponse.model_validate(item)


def reservation_list(
    db: Session,
    org: UUID,
    property_id: UUID | None,
    channel: Channel | None,
    from_date: date | None,
    to_date: date | None,
    status: str | None,
    limit: int,
    offset: int,
) -> ReservationList:
    if property_id:
        get_property(db, org, property_id)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(422, "시작일은 종료일 이후일 수 없습니다.")
    items, total = repo.list_reservations(
        db, org, property_id, channel, from_date, to_date, status, limit, offset
    )
    return ReservationList(
        items=[ReservationResponse.model_validate(item) for item in items], total=total
    )
