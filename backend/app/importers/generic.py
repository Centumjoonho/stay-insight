"""Generic owner CSV only. Channel labels do not select a provider-specific format."""

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from fastapi import HTTPException

from app.schemas.imports import ColumnMapping, RowError, ValidationResponse

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_COLUMNS = 64
MAX_CELL = 4096
MAX_ERRORS = 100


@dataclass
class CsvDocument:
    filename: str
    checksum: str
    encoding: str
    headers: list[str]
    rows: list[list[str]]
    warnings: list[str]


@dataclass
class NormalizedRow:
    external_reservation_id: str
    check_in: date
    check_out: date
    booked_nights: int
    guest_count: int | None
    gross_revenue: Decimal
    channel_fee: Decimal | None
    net_revenue: Decimal | None
    reservation_status: str


class CsvAdapter(Protocol):
    def normalize(
        self, document: CsvDocument, mapping: ColumnMapping
    ) -> tuple[list[NormalizedRow], ValidationResponse]: ...


def parse_csv(filename: str, data: bytes) -> CsvDocument:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if not name.lower().endswith(".csv") or len(name) > 200 or any(ord(c) < 32 for c in name):
        raise HTTPException(422, "유효한 .csv 파일 이름이 필요합니다.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "CSV 파일은 5 MiB 이하여야 합니다.")
    if not data or b"\x00" in data:
        raise HTTPException(422, "비어 있거나 지원하지 않는 CSV 파일입니다.")
    encoding = "utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        content = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp949"
        try:
            content = data.decode(encoding)
        except UnicodeDecodeError as error:
            raise HTTPException(422, "UTF-8 또는 CP949 CSV가 필요합니다.") from error
    if any(ord(c) < 32 and c not in "\r\n\t" for c in content):
        raise HTTPException(422, "CSV에 지원하지 않는 제어 문자가 있습니다.")
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        headers = next(reader)
        if (
            not 1 <= len(headers) <= MAX_COLUMNS
            or any(not h.strip() or h != h.strip() or len(h) > 100 for h in headers)
            or len(set(headers)) != len(headers)
        ):
            raise ValueError
        rows: list[list[str]] = []
        formula = False
        for row in reader:
            if len(row) != len(headers) or any(len(cell) > MAX_CELL for cell in row):
                raise ValueError
            rows.append(row)
            formula |= any(cell.lstrip().startswith(("=", "+", "-", "@")) for cell in row)
            if len(rows) > MAX_ROWS:
                raise HTTPException(413, "CSV는 10,000행 이하여야 합니다.")
        if not rows:
            raise ValueError
    except (csv.Error, StopIteration, ValueError) as error:
        raise HTTPException(422, "CSV 헤더, 따옴표 또는 행의 열 개수를 확인해 주세요.") from error
    warnings = ["모든 열은 텍스트로 처리됩니다. 수식은 실행되지 않습니다."] if formula else []
    if encoding == "cp949":
        warnings.append("CP949로 해석했습니다. 미리보기의 한글을 확인해 주세요.")
    return CsvDocument(name, hashlib.sha256(data).hexdigest(), encoding, headers, rows, warnings)


def money(value: str) -> Decimal:
    # Exact whole KRW only; never infer currency, tax basis or gross from net.
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.0{1,2})?", value):
        raise ValueError
    result = Decimal(value.replace(",", ""))
    if result > Decimal("999999999999999999"):
        raise ValueError
    return result


class GenericCsvAdapter:
    def normalize(
        self, document: CsvDocument, mapping: ColumnMapping
    ) -> tuple[list[NormalizedRow], ValidationResponse]:
        columns = mapping.model_dump(exclude_none=True)
        if len(set(columns.values())) != len(columns) or any(
            header not in document.headers for header in columns.values()
        ):
            raise HTTPException(422, "각 항목에 서로 다른 실제 CSV 열을 연결해 주세요.")
        indexes = {field: document.headers.index(header) for field, header in columns.items()}
        normalized: list[NormalizedRow] = []
        errors: list[RowError] = []
        invalid = 0
        seen: set[str] = set()
        for number, row in enumerate(document.rows, start=2):
            values = {field: row[index].strip() for field, index in indexes.items()}
            field = "external_reservation_id"
            try:
                external_id = values[field]
                if (
                    not external_id
                    or len(external_id) > 200
                    or external_id in seen
                    or external_id.startswith(("=", "+", "-", "@"))
                ):
                    raise ValueError
                seen.add(external_id)
                field = "check_in"
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values[field]):
                    raise ValueError
                check_in = date.fromisoformat(values[field])
                field = "check_out"
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values[field]):
                    raise ValueError
                check_out = date.fromisoformat(values[field])
                if check_out <= check_in:
                    raise ValueError
                field = "gross_revenue"
                gross = money(values[field])
                field = "channel_fee"
                fee = money(values[field]) if values.get(field) else None
                if fee is not None and fee > gross:
                    raise ValueError
                field = "guest_count"
                guest = None
                if values.get(field):
                    if not re.fullmatch(r"[0-9]{1,6}", values[field]):
                        raise ValueError
                    guest = int(values[field])
                    if guest < 1:
                        raise ValueError
                field = "reservation_status"
                status = values.get(field) or "UNKNOWN"
                if status not in {"CONFIRMED", "CANCELLED", "UNKNOWN"}:
                    raise ValueError
                normalized.append(
                    NormalizedRow(
                        external_id,
                        check_in,
                        check_out,
                        (check_out - check_in).days,
                        guest,
                        gross,
                        fee,
                        gross - fee if fee is not None else None,
                        status,
                    )
                )
            except ValueError:
                invalid += 1
                if len(errors) < MAX_ERRORS:
                    errors.append(
                        RowError(
                            row=number,
                            field=field,
                            message="형식, 범위 또는 예약번호 중복을 확인해 주세요.",
                        )
                    )
        return normalized, ValidationResponse(
            total_rows=len(document.rows),
            valid_rows=len(normalized),
            invalid_rows=invalid,
            errors=errors,
            errors_truncated=invalid > MAX_ERRORS,
            warnings=document.warnings
            + [
                "KRW 정수, YYYY-MM-DD 날짜, 상태 CONFIRMED/CANCELLED/UNKNOWN만 지원합니다.",
                "오류가 있으면 전체 가져오기를 취소합니다. 기존 예약번호는 현재 값으로 갱신합니다.",
                "순매출은 입력한 총 매출 - 수수료이며 정산액이나 KPI가 아닙니다.",
            ],
        )
