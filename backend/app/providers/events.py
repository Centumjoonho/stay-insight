"""Official festival adapter; no images, deprecated geography or credential diagnostics."""

import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, build_opener

from app.providers.lodgings_api import NoRedirect

SOURCE = "KTO_TOURAPI_EVENTS"
DATASET = "한국관광공사_국문 관광정보 서비스_GW"
SOURCE_URL = "https://www.data.go.kr/data/15101578/openapi.do"
ENDPOINT = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"
REGIONS = {
    "110": "중구",
    "140": "서구",
    "170": "동구",
    "200": "영도구",
    "230": "부산진구",
    "260": "동래구",
    "290": "남구",
    "320": "북구",
    "350": "해운대구",
    "380": "사하구",
    "410": "금정구",
    "440": "강서구",
    "470": "연제구",
    "500": "수영구",
    "530": "사상구",
    "710": "기장군",
}
# Small known-working page size; at most 100 pages/300 HTTP attempts.
PAGE_SIZE = 2
MAX_PAGES = 100
MAX_BYTES = 2 * 1024 * 1024


class EventError(Exception):
    """Fixed internal codes only."""


@dataclass(frozen=True)
class EventRecord:
    source_event_id: str
    district: str
    title: str
    start_date: date
    end_date: date
    address: str | None
    source_status: str | None


def day(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        raise ValueError("Invalid date")
    return datetime.strptime(value, "%Y%m%d").date()


def optional(value: object, maximum: int) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Invalid text")
    return value


def parse_page(payload: object, page: int) -> tuple[int, list[EventRecord]]:
    try:
        if not isinstance(payload, dict):
            raise ValueError
        response = payload["response"]
        if response["header"]["resultCode"] != "0000":
            raise ValueError
        body = response["body"]
        total, size, number = (body[k] for k in ("totalCount", "numOfRows", "pageNo"))
        if any(type(n) is not int for n in (total, size, number)):
            raise ValueError
        if number != page or not 0 <= total <= PAGE_SIZE * MAX_PAGES:
            raise ValueError
        # No live empty shape assumed: ambiguous empty responses fail closed.
        if total == 0:
            raise EventError("EVENT_EMPTY_CONTRACT_UNVERIFIED")
        rows = body["items"]["item"]
        if (
            not isinstance(rows, list)
            or len(rows) != size
            or size != min(PAGE_SIZE, total - (page - 1) * PAGE_SIZE)
            or size <= 0
        ):
            raise ValueError
        result = []
        for row in rows:
            identity = row["contentid"]
            title = row["title"]
            district = row["lDongSignguCd"]
            if (
                not isinstance(identity, str)
                or not re.fullmatch(r"[0-9]{1,40}", identity)
                or not isinstance(title, str)
                or not title.strip()
                or len(title) > 500
                or row["lDongRegnCd"] != "26"
                or district not in REGIONS
            ):
                raise ValueError
            start, end = day(row["eventstartdate"]), day(row["eventenddate"])
            if end < start:
                raise ValueError
            address = (
                " ".join(
                    filter(None, [optional(row.get("addr1"), 500), optional(row.get("addr2"), 500)])
                )
                or None
            )
            result.append(
                EventRecord(
                    identity,
                    district,
                    title,
                    start,
                    end,
                    address,
                    optional(row.get("progresstype"), 100),
                )
            )
        return total, result
    except EventError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise EventError("EVENT_INVALID_RESPONSE") from exc


class OfficialEventProvider:
    def __init__(self, key: str):
        self.key = key

    def request(self, start: date, end: date, page: int) -> object:
        if not self.key.strip():
            raise EventError("EVENT_KEY_REQUIRED")
        query = urlencode(
            {
                "serviceKey": unquote(self.key),
                "MobileOS": "ETC",
                "MobileApp": "StayInsight",
                "_type": "json",
                "arrange": "A",
                "numOfRows": PAGE_SIZE,
                "pageNo": page,
                "lDongRegnCd": "26",
                "eventStartDate": start.strftime("%Y%m%d"),
                "eventEndDate": end.strftime("%Y%m%d"),
            }
        )
        for attempt in range(3):
            try:
                with build_opener(NoRedirect()).open(
                    Request(ENDPOINT + "?" + query), timeout=20
                ) as response:
                    raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise EventError("EVENT_RESPONSE_TOO_LARGE")
                try:
                    return json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise EventError("EVENT_INVALID_RESPONSE") from exc
            except HTTPError as exc:
                if (exc.code != 429 and exc.code < 500) or attempt == 2:
                    raise EventError("EVENT_HTTP_ERROR") from None
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise EventError("EVENT_NETWORK_ERROR") from None
            time.sleep(attempt + 1)
        raise EventError("EVENT_NETWORK_ERROR")

    def fetch(self, start: date, end: date) -> list[EventRecord]:
        if type(start) is not date or type(end) is not date or not 0 <= (end - start).days <= 210:
            raise EventError("EVENT_INVALID_WINDOW")
        result: list[EventRecord] = []
        ids: set[str] = set()
        expected = None
        for page in range(1, MAX_PAGES + 1):
            total, rows = parse_page(self.request(start, end, page), page)
            if expected is not None and total != expected:
                raise EventError("EVENT_SNAPSHOT_CHANGED")
            expected = total
            for row in rows:
                if row.source_event_id in ids:
                    raise EventError("EVENT_DUPLICATE_ID")
                if row.end_date < start or row.start_date > end:
                    raise EventError("EVENT_OUTSIDE_WINDOW")
                ids.add(row.source_event_id)
                result.append(row)
            if len(result) == total:
                return result
        raise EventError("EVENT_PAGE_LIMIT")
