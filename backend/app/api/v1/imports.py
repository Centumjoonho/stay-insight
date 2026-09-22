from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.api.dependencies.tenant import CurrentUser, Database, OrganizationContext
from app.importers.generic import MAX_BYTES
from app.models.imports import Channel, ReservationStatus
from app.schemas.imports import (
    ImportList,
    ImportResponse,
    PreviewResponse,
    ReservationList,
    ReservationResponse,
    ValidationResponse,
)
from app.services import imports as service

router = APIRouter()
CsvFile = Annotated[UploadFile, File()]


def read_file(file: UploadFile) -> bytes:
    try:
        data = file.file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "CSV 파일은 5 MiB 이하여야 합니다.")
        return data
    finally:
        file.file.close()


@router.post("/imports/preview", response_model=PreviewResponse)
def preview(file: CsvFile, user: CurrentUser) -> PreviewResponse:
    return service.preview(file.filename or "", read_file(file))


@router.post("/imports/validate", response_model=ValidationResponse)
def validate(
    file: CsvFile,
    db: Database,
    org: OrganizationContext,
    property_id: Annotated[UUID, Form()],
    channel: Annotated[Channel, Form()],
    column_mapping: Annotated[str, Form(max_length=8192)],
) -> ValidationResponse:
    return service.validate(
        db,
        org,
        property_id,
        file.filename or "",
        read_file(file),
        service.mapping_from_json(column_mapping),
    )


@router.post("/imports", response_model=ImportResponse)
def import_csv(
    file: CsvFile,
    db: Database,
    org: OrganizationContext,
    user: CurrentUser,
    property_id: Annotated[UUID, Form()],
    channel: Annotated[Channel, Form()],
    column_mapping: Annotated[str, Form(max_length=8192)],
) -> ImportResponse:
    return service.import_csv(
        db,
        org,
        user.user_id,
        property_id,
        channel,
        file.filename or "",
        read_file(file),
        service.mapping_from_json(column_mapping),
    )


@router.get("/imports", response_model=ImportList)
def imports(
    db: Database,
    org: OrganizationContext,
    property_id: UUID | None = None,
    channel: Channel | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ImportList:
    return service.import_list(db, org, property_id, channel, limit, offset)


@router.get("/imports/{import_id}", response_model=ImportResponse)
def import_detail(import_id: UUID, db: Database, org: OrganizationContext) -> ImportResponse:
    return service.import_detail(db, org, import_id)


@router.get("/reservations", response_model=ReservationList)
def reservations(
    db: Database,
    org: OrganizationContext,
    property_id: UUID | None = None,
    channel: Channel | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    reservation_status: ReservationStatus | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReservationList:
    return service.reservation_list(
        db, org, property_id, channel, from_date, to_date, reservation_status, limit, offset
    )


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
def reservation_detail(
    reservation_id: UUID,
    db: Database,
    org: OrganizationContext,
) -> ReservationResponse:
    return service.reservation_detail(db, org, reservation_id)
