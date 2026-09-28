"""Normalized accommodation provider contract; live mapping lives in lodgings_api."""

from datetime import date
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

SOURCE = "MOIS_LODGINGS"
DATASET = "행정안전부_문화_숙박업"
SOURCE_URL = "https://www.data.go.kr/data/15155124/openapi.do"
BUSAN_DISTRICTS = (
    "중구",
    "서구",
    "동구",
    "영도구",
    "부산진구",
    "동래구",
    "남구",
    "북구",
    "해운대구",
    "사하구",
    "금정구",
    "강서구",
    "연제구",
    "수영구",
    "사상구",
    "기장군",
)
Status = Literal["OPEN", "CLOSED", "SUSPENDED", "UNKNOWN"]
LicenseType = Literal["GENERAL_ACCOMMODATION", "TOURIST_HOTEL", "LIFESTYLE_ACCOMMODATION", "OTHER"]


class LicenseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_record_id: str = Field(min_length=1, max_length=200)
    business_name: str = Field(min_length=1, max_length=300)
    source_license_type: str = Field(max_length=200)
    normalized_license_type: LicenseType = "OTHER"
    source_business_status: str = Field(max_length=200)
    normalized_business_status: Status = "UNKNOWN"
    sigungu_name: str
    license_date: date | None = None
    closure_date: date | None = None
    source_updated_at: AwareDatetime | None = None


class ProviderBatch(BaseModel):
    records: list[LicenseRecord] = Field(max_length=200000)
    # Explicit, complete coverage is required even for a genuine zero-row district.
    covered_districts: list[str]
    source_reference_date: date | None = None
    closure_dates_supported: bool = False
    failed_count: int = Field(default=0, ge=0)
    complete: bool = True


class AccommodationProvider(Protocol):
    def fetch(self) -> ProviderBatch: ...


class ProviderUnavailable(Exception):
    pass


class OfficialAccommodationProvider:
    def fetch(self) -> ProviderBatch:
        from app.providers.lodgings_api import fetch

        return fetch()


def normalize_type(value: str) -> LicenseType:
    # No upstream category mapping has been verified. Preserve the source value.
    return "OTHER"


def normalize_status(value: str) -> Status:
    # Non-open must never be treated as closed without verified provider semantics.
    return "UNKNOWN"


def normalize_district(value: str) -> str:
    if value not in BUSAN_DISTRICTS:
        raise ValueError("Unsupported Busan district")
    return value
