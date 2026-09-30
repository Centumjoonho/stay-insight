"""TEST/DEVELOPMENT ONLY: captured wire contract, not a production adapter.

Mutations below are negative test inputs, never claimed as captured responses.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

FIXTURES = Path(__file__).parent / "fixtures" / "tourism_visitors"
BUSAN = {
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
CATEGORIES = {"1": "현지인(a)", "2": "외지인(b)", "3": "외국인(c)"}


class WireItem(BaseModel):
    """Strict verification harness only; not imported by application code."""

    model_config = ConfigDict(extra="forbid")
    signguCode: str
    signguNm: str
    daywkDivCd: str
    daywkDivNm: str
    touDivCd: str
    touDivNm: str
    touNum: Decimal
    baseYmd: str

    @field_validator("touNum", mode="before")
    @classmethod
    def exact_number(cls, value: object) -> Decimal:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Expected captured decimal string")
        parsed = Decimal(value)
        if not parsed.is_finite() or parsed < 0:
            raise ValueError("Invalid estimate")
        return parsed

    @field_validator("baseYmd")
    @classmethod
    def valid_day(cls, value: str) -> str:
        if len(value) != 8 or not value.isdigit():
            raise ValueError("Invalid day")
        datetime.strptime(value, "%Y%m%d")
        return value


def captured(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def parse_capture(payload: dict[str, Any]) -> list[WireItem]:
    if "response" not in payload:
        raise ValueError("Non-success envelope")
    response = payload["response"]
    if response["header"] != {"resultCode": "0000", "resultMsg": "OK"}:
        raise ValueError("Non-success result")
    body = response["body"]
    if body["items"] == "":
        if body["totalCount"] != 0 or body["numOfRows"] != 0:
            raise ValueError("Inconsistent empty response")
        return []
    rows = body["items"]["item"]
    if not isinstance(rows, list) or len(rows) != body["numOfRows"]:
        raise ValueError("Invalid page")
    return [WireItem.model_validate(row) for row in rows]


def test_actual_envelope_fields_decimal_and_busan_categories() -> None:
    payload = captured("daily.json")
    assert payload["response"]["body"]["pageNo"] == 1
    assert payload["response"]["body"]["totalCount"] == 807
    rows = parse_capture(payload)
    assert len(rows) == 807
    assert rows[0].touNum == Decimal("113946.0")
    busan = [row for row in rows if row.signguCode in BUSAN]
    assert len(busan) == 48
    assert {(row.signguCode, row.touDivCd) for row in busan} == {
        (code, category) for code in BUSAN for category in CATEGORIES
    }
    for row in busan:
        assert row.signguNm == BUSAN[row.signguCode]
        assert row.touDivNm == CATEGORIES[row.touDivCd]
        assert row.baseYmd == "20260801"
        assert (row.daywkDivCd, row.daywkDivNm) == ("6", "토요일")


@pytest.mark.parametrize("name", ["empty.json", "invalid.json"])
def test_real_empty_and_malformed_date_are_empty_success(name: str) -> None:
    assert parse_capture(captured(name)) == []


def test_real_missing_parameter_has_separate_error_envelope() -> None:
    payload = captured("missing_parameter.txt")
    assert payload["resultCode"] == "11"
    with pytest.raises(ValueError, match="Non-success envelope"):
        parse_capture(payload)


@pytest.mark.parametrize("value", [None, "", "NaN", "Infinity", "-1", 1.5, True])
def test_unobserved_null_blank_and_invalid_numbers_are_not_zero(value: object) -> None:
    row = captured("daily.json")["response"]["body"]["items"]["item"][0]
    row["touNum"] = value
    with pytest.raises(ValidationError):
        WireItem.model_validate(row)


def test_missing_value_rejected_and_exact_decimal_preserved() -> None:
    row = captured("daily.json")["response"]["body"]["items"]["item"][0]
    row["touNum"] = "0"
    assert WireItem.model_validate(row).touNum == Decimal(0)
    row["touNum"] = "123.4567890123456789"
    assert WireItem.model_validate(row).touNum == Decimal("123.4567890123456789")
    del row["touNum"]
    with pytest.raises(ValidationError):
        WireItem.model_validate(row)


def test_real_singleton_page_still_uses_array() -> None:
    assert len(parse_capture(captured("boundary.json"))) == 1


def test_inconsistent_empty_and_failed_header_rejected() -> None:
    payload = captured("empty.json")
    payload["response"]["body"]["totalCount"] = 1
    with pytest.raises(ValueError, match="Inconsistent"):
        parse_capture(payload)
    payload = captured("daily.json")
    payload["response"]["header"]["resultCode"] = "03"
    with pytest.raises(ValueError, match="Non-success"):
        parse_capture(payload)


def test_fixtures_have_no_credentials_or_urls() -> None:
    for name in [
        "daily.json",
        "empty.json",
        "invalid.json",
        "boundary.json",
        "missing_parameter.txt",
    ]:
        content = (FIXTURES / name).read_text(encoding="utf-8")
        assert "serviceKey" not in content
        assert "http://" not in content and "https://" not in content
