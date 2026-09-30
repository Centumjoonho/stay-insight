"""Source-gated visitor contract; no HTTP, database, monthly aggregation or fixtures.

The verified candidate documents DAILY observations. This is not a live adapter.
See docs/tourism-visitor-source.md before implementing a provider or persistence.
"""

from datetime import date
from decimal import Decimal
from typing import Final, Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

SOURCE_URL: Final = "https://www.data.go.kr/data/15101972/openapi.do"
DATASET: Final = "한국관광공사_빅데이터_지역별 방문자수_GW"
GATE_ERROR = "LIVE_VISITOR_PROVIDER_NOT_VERIFIED"


class DailyVisitorObservation(BaseModel):
    """Internal proposal based on documented daily semantics, not a wire/DB schema.

    Source region/category codes are opaque until mappings are verified. A null
    value preserves missingness; it is never an observed zero. No monthly value
    can be represented by changing the period type or summing these records.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    source_dataset: Literal["한국관광공사_빅데이터_지역별 방문자수_GW"] = DATASET
    source_url: Literal["https://www.data.go.kr/data/15101972/openapi.do"] = SOURCE_URL
    scope_level: Literal["SIDO", "SIGUNGU"]
    source_region_code: str = Field(min_length=1)
    source_region_name: str = Field(min_length=1)
    reference_date: date
    period_type: Literal["DAY"] = "DAY"
    visitor_category_code: str = Field(min_length=1)
    visitor_category_name: str = Field(min_length=1)
    value: Decimal | None = Field(ge=0, allow_inf_nan=False)
    metric_name: Literal["추정 방문자 수"] = "추정 방문자 수"
    metric_unit: Literal["명"] = "명"
    is_estimated: Literal[True] = True
    methodology: Literal["이동통신 기반 일자별 순방문자 추정"] = (
        "이동통신 기반 일자별 순방문자 추정"
    )
    methodology_version: str | None = None
    source_updated_at: AwareDatetime | None = None
    collected_at: AwareDatetime

    @field_validator("value", mode="before")
    @classmethod
    def reject_inexact_value(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("Use an exact decimal string, Decimal, integer or null")
        return value


class VisitorProvider(Protocol):
    def fetch(self, start: date, end: date) -> tuple[DailyVisitorObservation, ...]: ...


class VisitorSourceUnverified(Exception):
    """Safe, fixed error; never contains a key, URL query or upstream payload."""


class UnverifiedVisitorProvider:
    """Explicit fail-closed placeholder, independent of any configured API key."""

    def fetch(self, start: date, end: date) -> tuple[DailyVisitorObservation, ...]:
        raise VisitorSourceUnverified(GATE_ERROR)
