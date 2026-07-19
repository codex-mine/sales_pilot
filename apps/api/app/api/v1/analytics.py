"""Organization-wide analytics (Analytics domain). This module's first
route (email performance) reads from Email Tracking's raw EmailEvent data —
future analytics endpoints reading pre-aggregated Metric rows belong here
too, rather than each owning module inventing its own analytics prefix."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.email_tracking import EmailPerformanceAnalyticsResponse
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
