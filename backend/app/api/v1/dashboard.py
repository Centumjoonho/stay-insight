from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies.tenant import Database, OrganizationContext
from app.schemas.dashboard import DashboardSummary, DashboardTrends
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    month: str | None = Query(None, max_length=7),
) -> DashboardSummary:
    return service.summary(db, org, property_id, month)


@router.get("/trends", response_model=DashboardTrends)
def trends(
    db: Database,
    org: OrganizationContext,
    property_id: UUID,
    months: int = Query(12, ge=1, le=24),
    month: str | None = Query(None, max_length=7),
) -> DashboardTrends:
    return service.trends(db, org, property_id, months, month)
