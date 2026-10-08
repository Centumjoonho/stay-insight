from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies.tenant import Database, OrganizationContext
from app.schemas.dashboard_v2 import DashboardSummaryV2, DashboardTrendsV2
from app.services import dashboard_v2 as service

router = APIRouter(prefix="/dashboard-v2", tags=["dashboard-v2"])


@router.get("/summary", response_model=DashboardSummaryV2)
def summary(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    month: str | None = Query(None, max_length=7),
) -> DashboardSummaryV2:
    return service.summary(db, org, property_id, month)


@router.get("/trends", response_model=DashboardTrendsV2)
def trends(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    months: int = Query(12, ge=1, le=24),
    month: str | None = Query(None, max_length=7),
) -> DashboardTrendsV2:
    return service.trends(db, org, property_id, months, month)
