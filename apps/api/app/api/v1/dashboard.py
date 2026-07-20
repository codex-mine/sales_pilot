"""Dashboard summary + per-user widget layout CRUD (Analytics domain)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.analytics import (
    CreateDashboardWidgetRequest,
    DashboardSummaryResponse,
    DashboardWidgetResponse,
    UpdateDashboardWidgetRequest,
)
from app.schemas.analytics_serializers import serialize_dashboard_widget
from app.schemas.common import ApiResponse
from app.services.analytics.dashboard_service import DashboardService
from app.services.analytics.dashboard_widget_service import DashboardWidgetService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
async def get_dashboard_summary(
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DashboardSummaryResponse]:
    summary = await DashboardService(db).get_dashboard_summary(user.organization_id, user.id)
    return ApiResponse(data=summary)


@router.get("/widgets", response_model=ApiResponse[list[DashboardWidgetResponse]])
async def list_dashboard_widgets(
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DashboardWidgetResponse]]:
    widgets = await DashboardWidgetService(db).list_for_user(user.organization_id, user.id)
    return ApiResponse(data=[serialize_dashboard_widget(w) for w in widgets])


@router.post("/widgets", response_model=ApiResponse[DashboardWidgetResponse], status_code=201)
async def create_dashboard_widget(
    payload: CreateDashboardWidgetRequest,
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DashboardWidgetResponse]:
    widget = await DashboardWidgetService(db).create(user.organization_id, user.id, payload=payload, actor=user)
    return ApiResponse(data=serialize_dashboard_widget(widget), message="Widget added.")


@router.patch("/widgets/{widget_id}", response_model=ApiResponse[DashboardWidgetResponse])
async def update_dashboard_widget(
    widget_id: uuid.UUID,
    payload: UpdateDashboardWidgetRequest,
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DashboardWidgetResponse]:
    service = DashboardWidgetService(db)
    widget = await service.require_widget(widget_id, user.organization_id)
    widget = await service.update(widget, payload=payload, actor=user)
    return ApiResponse(data=serialize_dashboard_widget(widget), message="Widget updated.")


@router.delete("/widgets/{widget_id}", response_model=ApiResponse[None])
async def delete_dashboard_widget(
    widget_id: uuid.UUID,
    user: User = Depends(require_permission("analytics", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = DashboardWidgetService(db)
    widget = await service.require_widget(widget_id, user.organization_id)
    await service.delete(widget, actor=user)
    return ApiResponse(message="Widget removed.")
