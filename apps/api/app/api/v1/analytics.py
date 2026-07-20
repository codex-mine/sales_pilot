"""Organization-wide analytics (Analytics domain). This module's first
route (email performance) reads from Email Tracking's raw EmailEvent data —
future analytics endpoints reading pre-aggregated Metric rows belong here
too, rather than each owning module inventing its own analytics prefix.

Module 12 adds pipeline-funnel / ai-usage / campaign-performance — the
drill-down detail endpoints behind the dashboard summary's three
Metric-backed widgets (see `dashboard_service.py`)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.analytics import (
    AIUsageAnalyticsResponse,
    CampaignPerformanceResponse,
    PipelineFunnelResponse,
)
from app.schemas.common import ApiResponse
from app.schemas.email_tracking import EmailPerformanceAnalyticsResponse
from app.services.analytics.dashboard_service import DashboardService
from app.services.email.email_tracking_service import EmailTrackingService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/email-performance", response_model=ApiResponse[EmailPerformanceAnalyticsResponse])
async def get_email_performance_analytics(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailPerformanceAnalyticsResponse]:
    analytics = await EmailTrackingService(db).get_performance_analytics(user.organization_id, days=days)
    return ApiResponse(data=EmailPerformanceAnalyticsResponse(**analytics))


@router.get("/pipeline-funnel", response_model=ApiResponse[PipelineFunnelResponse])
async def get_pipeline_funnel(
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PipelineFunnelResponse]:
    return ApiResponse(data=await DashboardService(db).get_pipeline_funnel(user.organization_id))


@router.get("/ai-usage", response_model=ApiResponse[AIUsageAnalyticsResponse])
async def get_ai_usage_analytics(
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIUsageAnalyticsResponse]:
    return ApiResponse(data=await DashboardService(db).get_ai_usage(user.organization_id))


@router.get("/campaign-performance", response_model=ApiResponse[CampaignPerformanceResponse])
async def get_campaign_performance_analytics(
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignPerformanceResponse]:
    return ApiResponse(data=await DashboardService(db).get_campaign_performance(user.organization_id, limit=limit))
