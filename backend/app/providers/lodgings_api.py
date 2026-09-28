"""Bounded MOIS JSON ingestion; never expose upstream URLs, keys or raw rows."""

import json
import os
import re
import time
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from app.providers.accommodation import (
    BUSAN_DISTRICTS,
    LicenseRecord,
    ProviderBatch,
    ProviderUnavailable,
)

ENDPOINT = "https://apis.data.go.kr/1741000/lodgings/info"
PAGE_SIZE = 100
MAX_ROWS = 200000
MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def request_page(key: str, page: int) -> dict[str, Any]:
    query = urlencode(
        {"serviceKey": unquote(key), "pageNo": page, "numOfRows": PAGE_SIZE, "returnType": "json"}
    )
    opener = build_opener(NoRedirect())
    for attempt in range(3):
        try:
            with opener.open(Request(ENDPOINT + "?" + query), timeout=30) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ProviderUnavailable("API_RESPONSE_TOO_LARGE")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ProviderUnavailable("API_INVALID_RESPONSE")
            return payload
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise ProviderUnavailable("API_HTTP_ERROR") from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ProviderUnavailable("API_NETWORK_ERROR") from None
        except (ValueError, UnicodeError):
            raise ProviderUnavailable("API_INVALID_RESPONSE") from None
        time.sleep(2**attempt)
    raise ProviderUnavailable("API_NETWORK_ERROR")


def field(row: dict[str, Any], name: str) -> str:
    value = row[name]
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Unexpected field type")
    return value.strip()


def source_id(row: dict[str, Any]) -> str:
    authority, number = field(row, "OPN_ATMY_GRP_CD"), field(row, "MNG_NO")
    if not authority or not number:
        raise ValueError("Missing source identity")
    return authority + ":" + number


def parse_date(value: str) -> date | None:
    if not value:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid source date")
    return date.fromisoformat(value)


def busan_record(row: dict[str, Any]) -> LicenseRecord | None:
    addresses = [field(row, "ROAD_NM_ADDR"), field(row, "LOTNO_ADDR")]
    districts: set[str] = set()
    for address in addresses:
        parts = address.split()
        if parts and parts[0] in {"부산광역시", "부산시", "부산"}:
            if len(parts) < 2 or parts[1] not in BUSAN_DISTRICTS:
                raise ValueError("Unrecognized Busan address")
            districts.add(parts[1])
    if not districts:
        if not any(addresses):
            raise ValueError("Cannot establish geography")
        return None
    if len(districts) != 1 or any(
        address and address.split()[0] not in {"부산광역시", "부산시", "부산"}
        for address in addresses
    ):
        raise ValueError("Conflicting geography")
    # Require BOTH code and source label; cancellations/unknown codes are not closures.
    status = field(row, "SALS_STTS_CD")
    label = field(row, "SALS_STTS_NM")
    detail = field(row, "DTL_SALS_STTS_CD")
    detail_label = field(row, "DTL_SALS_STTS_NM")
    normalized = "UNKNOWN"
    if (status, label, detail, detail_label) == ("01", "영업/정상", "01", "영업"):
        normalized = "OPEN"
    elif (status, label, detail_label) == ("03", "폐업", "폐업"):
        normalized = "CLOSED"
    elif (status, label, detail_label) == ("02", "휴업", "휴업"):
        normalized = "SUSPENDED"
    kind = field(row, "BZSTAT_SE_NM")
    normalized_kind = {
        "숙박업(생활)": "LIFESTYLE_ACCOMMODATION",
        "일반호텔": "GENERAL_ACCOMMODATION",
        "숙박업(일반)": "GENERAL_ACCOMMODATION",
    }.get(kind, "OTHER")
    updated = field(row, "DAT_UPDT_PNT")
    updated_at = None
    if updated:
        updated_at = datetime.strptime(updated, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=ZoneInfo("Asia/Seoul")
        )
    return LicenseRecord.model_validate(
        {
            "source_record_id": source_id(row),
            "business_name": field(row, "BPLC_NM"),
            "source_license_type": kind,
            "normalized_license_type": normalized_kind,
            "source_business_status": f"{status}:{label}|{detail}:{detail_label}",
            "normalized_business_status": normalized,
            "sigungu_name": next(iter(districts)),
            "license_date": parse_date(field(row, "LCPMT_YMD")),
            "closure_date": parse_date(field(row, "CLSBIZ_YMD")),
            "source_updated_at": updated_at,
        }
    )


def fetch() -> ProviderBatch:
    key = os.environ.get("PUBLIC_ACCOMMODATION_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable("API_KEY_REQUIRED")
    records: list[LicenseRecord] = []
    seen: set[str] = set()
    total: int | None = None
    first_ids: list[str] = []
    page = 1
    try:
        while True:
            payload = request_page(key, page)["response"]
            if str(payload["header"]["resultCode"]) != "0":
                raise ProviderUnavailable("API_RESULT_ERROR")
            body = payload["body"]
            count = int(body["totalCount"])
            size = int(body["numOfRows"])
            if not 0 < count <= MAX_ROWS or size != PAGE_SIZE or int(body["pageNo"]) != page:
                raise ProviderUnavailable("API_INCOMPLETE_PAGE")
            if total is not None and total != count:
                raise ProviderUnavailable("API_SNAPSHOT_CHANGED")
            total = count
            rows = body["items"]["item"]
            if not isinstance(rows, list) or len(rows) != min(size, count - (page - 1) * size):
                raise ProviderUnavailable("API_INCOMPLETE_PAGE")
            ids = [source_id(row) for row in rows]
            if page == 1:
                first_ids = ids
            for row, identifier in zip(rows, ids, strict=True):
                if identifier in seen:
                    raise ProviderUnavailable("API_DUPLICATE_RECORD")
                seen.add(identifier)
                record = busan_record(row)
                if record is not None:
                    records.append(record)
            if len(seen) == total:
                break
            page += 1
        # Offset paging has no snapshot token. Detect leading changes before publishing.
        check = request_page(key, 1)["response"]
        if (
            str(check["header"]["resultCode"]) != "0"
            or int(check["body"]["totalCount"]) != total
            or [source_id(row) for row in check["body"]["items"]["item"]] != first_ids
        ):
            raise ProviderUnavailable("API_SNAPSHOT_CHANGED")
        return ProviderBatch(
            records=records, covered_districts=list(BUSAN_DISTRICTS), closure_dates_supported=True
        )
    except ProviderUnavailable:
        raise
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ProviderUnavailable("API_INVALID_RESPONSE") from None
