from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.providers.tourism_visitors import DATASET, SOURCE_URL
from app.providers.visitor_api import CATEGORIES, SOURCE


class VisitorCategory(BaseModel):
    code: str
    name: str


class VisitorScope(BaseModel):
    level: Literal["SIGUNGU"] = "SIGUNGU"
    name: str
    source_region_code: str


class DailyPoint(BaseModel):
    date: date
    value: Decimal | None


class Rolling(BaseModel):
    average_7d: Decimal | None = None
    average_28d: Decimal | None = None
    previous_7d_average: Decimal | None = None
    change_7d_percent: Decimal | None = None


class Coverage(BaseModel):
    requested_days: int
    available_days: int = 0
    missing_days: int = 0
    complete_7d: bool = False
    complete_28d: bool = False
    completeness: Literal["APPLICATION_COVERAGE_ONLY"] = "APPLICATION_COVERAGE_ONLY"


class VisitorSource(BaseModel):
    source: str = SOURCE
    provider: str = "한국관광공사"
    dataset: str = DATASET
    url: str = SOURCE_URL
    metric_label: str = "일별 추정 방문자"
    is_estimated: Literal[True] = True
    methodology: str = "이동통신 기반 일별 추정 지표; 구분별 별도 집계"
    methodology_version: str | None = None
    last_collected_at: datetime | None = None
    latest_reference_date: date | None = None
    days_since_latest_reference: int | None = None
    latest_sync_status: str | None = None


class VisitorMarket(BaseModel):
    property_id: UUID
    available: bool = False
    reason: str | None = None
    scope: VisitorScope | None = None
    category: VisitorCategory
    categories: list[VisitorCategory] = Field(
        default_factory=lambda: [VisitorCategory(code=k, name=v) for k, v in CATEGORIES.items()]
    )
    latest: DailyPoint | None = None
    rolling: Rolling = Field(default_factory=Rolling)
    history: list[DailyPoint] = Field(default_factory=list)
    source: VisitorSource = Field(default_factory=VisitorSource)
    coverage: Coverage
    warnings: list[str] = Field(
        default_factory=lambda: ["공식 데이터 제공 시차가 있을 수 있습니다."]
    )
    calculation_version: Literal["visitor-daily-v1"] = "visitor-daily-v1"
    source_category: Literal["public"] = "public"
