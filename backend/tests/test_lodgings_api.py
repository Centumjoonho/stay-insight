"""Synthetic upstream-shaped rows; no production data or credentials."""

import io
import time
from copy import deepcopy
from datetime import timedelta
from email.message import Message
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from app.providers import lodgings_api as api
from app.providers.accommodation import BUSAN_DISTRICTS, ProviderUnavailable


def row(number: str = "TEST-1", address: str = "부산광역시 수영구 테스트로 1") -> dict[str, str]:
    return {
        "OPN_ATMY_GRP_CD": "TEST",
        "MNG_NO": number,
        "BPLC_NM": "TEST ONLY",
        "ROAD_NM_ADDR": address,
        "LOTNO_ADDR": "",
        "SALS_STTS_CD": "01",
        "SALS_STTS_NM": "영업/정상",
        "DTL_SALS_STTS_CD": "01",
        "DTL_SALS_STTS_NM": "영업",
        "BZSTAT_SE_NM": "숙박업(생활)",
        "LCPMT_YMD": "2026-01-01",
        "CLSBIZ_YMD": "",
        "DAT_UPDT_PNT": "2026-09-24 22:09:00",
    }


def page(rows: list[dict[str, str]], number: int, total: int) -> dict[str, Any]:
    return {
        "response": {
            "header": {"resultCode": "0"},
            "body": {
                "items": {"item": rows},
                "pageNo": number,
                "numOfRows": 2,
                "totalCount": total,
            },
        }
    }


@pytest.fixture
def pages(monkeypatch: pytest.MonkeyPatch) -> dict[int, dict[str, Any]]:
    monkeypatch.setenv("PUBLIC_ACCOMMODATION_API_KEY", "TEST-SECRET")
    monkeypatch.setattr(api, "PAGE_SIZE", 2)
    values = {
        1: page([row(), row("TEST-2", "서울특별시 중구 테스트로 1")], 1, 3),
        2: page([row("TEST-3", "부산광역시 해운대구 테스트로 2")], 2, 3),
    }
    monkeypatch.setattr(api, "request_page", lambda key, number: deepcopy(values[number]))
    return values


def test_full_pagination_and_geography(pages: dict[int, dict[str, Any]]) -> None:
    batch = api.fetch()
    assert len(batch.records) == 2
    assert batch.covered_districts == list(BUSAN_DISTRICTS)
    assert batch.source_reference_date is None
    assert batch.closure_dates_supported
    item = batch.records[0]
    assert item.source_record_id == "TEST:TEST-1"
    assert item.normalized_business_status == "OPEN"
    assert item.normalized_license_type == "LIFESTYLE_ACCOMMODATION"
    assert item.source_updated_at and item.source_updated_at.utcoffset() == timedelta(hours=9)


@pytest.mark.parametrize("failure", ["short", "duplicate", "count", "page", "result", "schema"])
def test_rejects_partial_or_changed_response(
    pages: dict[int, dict[str, Any]], failure: str
) -> None:
    body = pages[2]["response"]["body"]
    if failure == "short":
        body["items"]["item"] = []
    elif failure == "duplicate":
        body["items"]["item"] = [row()]
    elif failure == "count":
        body["totalCount"] = 4
    elif failure == "page":
        body["pageNo"] = 1
    elif failure == "result":
        pages[2]["response"]["header"]["resultCode"] = "30"
    else:
        del body["items"]
    with pytest.raises(ProviderUnavailable, match="API_"):
        api.fetch()


def test_final_snapshot_check(
    pages: dict[int, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def request(key: str, number: int) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        result: dict[str, Any] = deepcopy(pages[number])
        if calls == 3:
            result["response"]["body"]["items"]["item"][0]["MNG_NO"] = "CHANGED"
        return result

    monkeypatch.setattr(api, "request_page", request)
    with pytest.raises(ProviderUnavailable, match="API_SNAPSHOT_CHANGED"):
        api.fetch()


@pytest.mark.parametrize(
    "status,label,detail,expected",
    [
        ("03", "폐업", "폐업", "CLOSED"),
        ("02", "휴업", "휴업", "SUSPENDED"),
        ("04", "취소/말소/만료/정지/중지", "취소", "UNKNOWN"),
        ("03", "영업/정상", "영업", "UNKNOWN"),
    ],
)
def test_status_requires_explicit_semantics(
    status: str, label: str, detail: str, expected: str
) -> None:
    value = row()
    value.update(SALS_STTS_CD=status, SALS_STTS_NM=label, DTL_SALS_STTS_NM=detail)
    item = api.busan_record(value)
    assert item and item.normalized_business_status == expected


def test_optional_dates_unknown_types_and_rejected_geography() -> None:
    value = row()
    value.update(LCPMT_YMD="", DAT_UPDT_PNT="", BZSTAT_SE_NM="UNRECOGNIZED")
    item = api.busan_record(value)
    assert item and item.license_date is None and item.normalized_license_type == "OTHER"
    value["LOTNO_ADDR"] = "부산광역시 중구 테스트로 1"
    with pytest.raises(ValueError):
        api.busan_record(value)
    value["LOTNO_ADDR"] = ""
    value["LCPMT_YMD"] = "2026-02-30"
    with pytest.raises(ValueError):
        api.busan_record(value)


@pytest.mark.parametrize("key", ["TEST+A/B==", "TEST%2BA%2FB%3D%3D"])
def test_key_encoded_once(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    class Opener:
        def open(self, request: object, timeout: int) -> io.BytesIO:
            query = parse_qs(urlsplit(request.full_url).query)  # type: ignore[attr-defined]
            assert query["serviceKey"] == ["TEST+A/B=="]
            assert query["returnType"] == ["json"]
            assert timeout == 30
            return io.BytesIO(b"{}")

    monkeypatch.setattr(api, "build_opener", lambda *args: Opener())
    assert api.request_page(key, 1) == {}


@pytest.mark.parametrize("code,expected_calls", [(401, 1), (302, 1), (429, 3), (503, 3)])
def test_bounded_retry_and_redaction(
    monkeypatch: pytest.MonkeyPatch, code: int, expected_calls: int
) -> None:
    calls = 0

    class Opener:
        def open(self, request: object, timeout: int) -> None:
            nonlocal calls
            calls += 1
            raise HTTPError(
                "https://example.invalid?serviceKey=SECRET", code, "SECRET", Message(), None
            )

    monkeypatch.setattr(api, "build_opener", lambda *args: Opener())
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    with pytest.raises(ProviderUnavailable) as error:
        api.request_page("SECRET", 1)
    assert str(error.value) == "API_HTTP_ERROR"
    assert calls == expected_calls


def test_oversized_and_non_json_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    class Opener:
        def open(self, request: object, timeout: int) -> io.BytesIO:
            return io.BytesIO(b"x" * 11)

    monkeypatch.setattr(api, "build_opener", lambda *args: Opener())
    monkeypatch.setattr(api, "MAX_BYTES", 10)
    with pytest.raises(ProviderUnavailable, match="API_RESPONSE_TOO_LARGE"):
        api.request_page("SECRET", 1)
    monkeypatch.setattr(api, "MAX_BYTES", 20)
    with pytest.raises(ProviderUnavailable, match="API_INVALID_RESPONSE"):
        api.request_page("SECRET", 1)
