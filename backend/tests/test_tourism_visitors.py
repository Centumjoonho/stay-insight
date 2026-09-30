"""TEST ONLY internal DTO inputs, not official API response fixtures/live values.

The documented daily fields/semantics motivate the contract. TEST identifiers and
numeric boundary values below test validation, not a claimed official mapping.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.providers.tourism_visitors import (
    GATE_ERROR,
    DailyVisitorObservation,
    UnverifiedVisitorProvider,
    VisitorProvider,
    VisitorSourceUnverified,
)


def observation(**changes: object) -> DailyVisitorObservation:
    return DailyVisitorObservation.model_validate(
        {
            "scope_level": "SIGUNGU",
            "source_region_code": "TEST-REGION",
            "source_region_name": "TEST ONLY region",
            "reference_date": date(2026, 1, 1),
            "visitor_category_code": "TEST-CATEGORY",
            "visitor_category_name": "TEST ONLY category",
            "value": "123.4567890123456789",
            "collected_at": datetime(2026, 2, 1, tzinfo=UTC),
        }
        | changes
    )


def test_preserves_exact_estimate_and_daily_provenance() -> None:
    item = observation()
    assert item.value == Decimal("123.4567890123456789")
    payload = json.loads(item.model_dump_json())
    assert payload["value"] == "123.4567890123456789"
    assert payload["period_type"] == "DAY"
    assert payload["metric_name"] == "추정 방문자 수"
    assert payload["is_estimated"] is True
    assert item.methodology_version is None
    assert item.source_updated_at is None
    assert item.source_region_code == "TEST-REGION"


def test_missing_is_not_zero_or_an_omitted_required_value() -> None:
    assert observation(value=None).value is None
    assert observation(value="0").value == Decimal(0)
    payload = observation().model_dump()
    del payload["value"]
    with pytest.raises(ValidationError):
        DailyVisitorObservation.model_validate(payload)


@pytest.mark.parametrize("value", [-1, "-0.01", "NaN", "Infinity", "-Infinity", 1.5, True, ""])
def test_rejects_invalid_or_inexact_observations(value: object) -> None:
    with pytest.raises(ValidationError):
        observation(value=value)


@pytest.mark.parametrize(
    "changes",
    [
        {"scope_level": "DONG"},
        {"source_region_code": " "},
        {"visitor_category_code": ""},
        {"reference_date": "2026-02-30"},
        {"reference_date": "2026-01"},
        {"period_type": "MONTH"},
        {"is_estimated": False},
        {"metric_name": "숙박객 수"},
        {"metric_unit": "객실"},
        {"collected_at": datetime(2026, 2, 1)},
        {"source_updated_at": datetime(2026, 2, 1)},
        {"organization_id": "TEST"},
    ],
)
def test_rejects_unsupported_semantics(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        observation(**changes)


def test_preserves_methodology_and_provider_update_separately() -> None:
    updated = datetime(2026, 1, 2, tzinfo=UTC)
    item = observation(methodology_version="TEST-ONLY-VERSION", source_updated_at=updated)
    assert item.methodology_version == "TEST-ONLY-VERSION"
    assert item.source_updated_at == updated
    assert item.collected_at > updated


def test_unverified_provider_fails_even_with_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOURISM_VISITOR_API_KEY", "TEST-SECRET-DO-NOT-LOG")
    provider: VisitorProvider = UnverifiedVisitorProvider()
    with pytest.raises(VisitorSourceUnverified) as failure:
        provider.fetch(date(2026, 1, 1), date(2026, 1, 31))
    assert str(failure.value) == GATE_ERROR
