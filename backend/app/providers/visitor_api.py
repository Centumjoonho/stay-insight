"""Verified daily KTO adapter. No owner data or credential-bearing diagnostics."""

import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from types import MappingProxyType
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, build_opener

from app.providers.lodgings_api import NoRedirect

SOURCE = "KTO_DATALAB_VISITORS_DAILY"
ENDPOINT = "https://apis.data.go.kr/B551011/DataLabService/locgoRegnVisitrDDList"
REGIONS = MappingProxyType(
    {
        "26110": "중구",
        "26140": "서구",
        "26170": "동구",
        "26200": "영도구",
        "26230": "부산진구",
        "26260": "동래구",
        "26290": "남구",
        "26320": "북구",
        "26350": "해운대구",
        "26380": "사하구",
        "26410": "금정구",
        "26440": "강서구",
        "26470": "연제구",
        "26500": "수영구",
        "26530": "사상구",
        "26710": "기장군",
    }
)
CATEGORIES = MappingProxyType({"1": "현지인(a)", "2": "외지인(b)", "3": "외국인(c)"})
PAGE_SIZE = 1000
MAX_PAGES = 10
MAX_BYTES = 4 * 1024 * 1024


class VisitorError(Exception):
    """Use fixed internal codes only, never upstream text."""


@dataclass(frozen=True)
class VisitorRecord:
    code: str
    name: str
    category: str
    category_name: str
    day: date
    value: Decimal
    weekday: str
    weekday_name: str


def parse_day(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        raise ValueError("Invalid calendar day")
    return datetime.strptime(value, "%Y%m%d").date()


def parse_page(payload: object, day: date, page: int) -> tuple[int, list[VisitorRecord]]:
    try:
        if not isinstance(payload, dict):
            raise ValueError
        response = payload["response"]
        if response["header"]["resultCode"] != "0000":
            raise ValueError
        body = response["body"]
        total, size, number = (body[k] for k in ("totalCount", "numOfRows", "pageNo"))
        if any(type(v) is not int for v in (total, size, number)):
            raise ValueError
        if number != page or not 0 <= total <= PAGE_SIZE * MAX_PAGES:
            raise ValueError
        if total == 0:
            if page != 1 or size != 0 or body["items"] != "":
                raise ValueError
            return 0, []
        rows = body["items"]["item"]
        if (
            not isinstance(rows, list)
            or len(rows) != size
            or size != min(PAGE_SIZE, total - (page - 1) * PAGE_SIZE)
            or size <= 0
        ):
            raise ValueError
        records = []
        for row in rows:
            names = (
                "signguCode",
                "signguNm",
                "touDivCd",
                "touDivNm",
                "touNum",
                "baseYmd",
                "daywkDivCd",
                "daywkDivNm",
            )
            if any(not isinstance(row[k], str) or not row[k] for k in names):
                raise ValueError
            code, category = row["signguCode"], row["touDivCd"]
            if not re.fullmatch(r"[0-9]{5}", code) or category not in CATEGORIES:
                raise ValueError
            if row["touDivNm"] != CATEGORIES[category] or parse_day(row["baseYmd"]) != day:
                raise ValueError
            if row["daywkDivCd"] != str(day.isoweekday()):
                raise ValueError
            if (
                row["daywkDivNm"]
                != ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")[
                    day.weekday()
                ]
            ):
                raise ValueError
            if not re.fullmatch(r"[0-9]{1,20}(?:\.[0-9]{1,20})?", row["touNum"]):
                raise ValueError
            value = Decimal(row["touNum"])
            if not value.is_finite() or value < 0:
                raise ValueError
            if code.startswith("26") and (code not in REGIONS or REGIONS[code] != row["signguNm"]):
                raise ValueError
            records.append(
                VisitorRecord(
                    code,
                    row["signguNm"],
                    category,
                    row["touDivNm"],
                    day,
                    value,
                    row["daywkDivCd"],
                    row["daywkDivNm"],
                )
            )
        return total, records
    except (KeyError, TypeError, ValueError, ArithmeticError):
        raise VisitorError("VISITOR_INVALID_RESPONSE") from None


class OfficialVisitorProvider:
    def __init__(self, key: str, max_requests: int = 450) -> None:
        self._key = key.strip()
        self.remaining = max_requests

    def request(self, day: date, page: int) -> object:
        if not self._key:
            raise VisitorError("VISITOR_KEY_REQUIRED")
        query = urlencode(
            {
                "serviceKey": unquote(self._key),
                "MobileOS": "ETC",
                "MobileApp": "StayInsight",
                "_type": "json",
                "pageNo": page,
                "numOfRows": PAGE_SIZE,
                "startYmd": day.strftime("%Y%m%d"),
                "endYmd": day.strftime("%Y%m%d"),
            }
        )
        for attempt in range(3):
            if self.remaining <= 0:
                raise VisitorError("VISITOR_REQUEST_BUDGET_EXCEEDED")
            self.remaining -= 1
            try:
                with build_opener(NoRedirect()).open(
                    Request(ENDPOINT + "?" + query), timeout=20
                ) as response:
                    raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise VisitorError("VISITOR_RESPONSE_TOO_LARGE")
                return json.loads(raw)
            except HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise VisitorError("VISITOR_HTTP_ERROR") from None
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise VisitorError("VISITOR_NETWORK_ERROR") from None
            except (ValueError, UnicodeError):
                raise VisitorError("VISITOR_INVALID_RESPONSE") from None
            time.sleep(2**attempt)
        raise VisitorError("VISITOR_NETWORK_ERROR")

    def fetch_day(self, day: date) -> list[VisitorRecord]:
        if type(day) is not date:
            raise VisitorError("VISITOR_INVALID_DATE")
        seen: set[tuple[str, str]] = set()
        result: list[VisitorRecord] = []
        expected: int | None = None
        for page in range(1, MAX_PAGES + 1):
            total, rows = parse_page(self.request(day, page), day, page)
            if expected is not None and total != expected:
                raise VisitorError("VISITOR_SNAPSHOT_CHANGED")
            expected = total
            for row in rows:
                pair = (row.code, row.category)
                if pair in seen:
                    raise VisitorError("VISITOR_DUPLICATE_ROW")
                seen.add(pair)
                if row.code in REGIONS:
                    result.append(row)
            if len(seen) == total:
                return result
        raise VisitorError("VISITOR_PAGE_LIMIT")
