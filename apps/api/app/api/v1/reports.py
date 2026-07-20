"""Saved/custom Reports CRUD + run-now delivery (Analytics domain)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.analytics import CreateReportRequest, ReportResponse, RunReportResponse, UpdateReportRequest
from app.schemas.analytics_serializers import serialize_report
from app.schemas.common import ApiResponse
from app.services.analytics.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ApiResponse[list[ReportResponse]])
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("reports", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ReportResponse]]:
    reports, total = await ReportService(db).list_for_organization(user.organization_id, page=page, page_size=page_size)
    return ApiResponse(data=[serialize_report(r) for r in reports], meta={"page": page, "page_size": page_size, "total": total})


@router.post("", response_model=ApiResponse[ReportResponse], status_code=201)
async def create_report(
    payload: CreateReportRequest,
    user: User = Depends(require_permission("reports", "create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ReportResponse]:
    report = await ReportService(db).create(user.organization_id, payload=payload, actor=user)
    return ApiResponse(data=serialize_report(report), message="Report created.")


@router.get("/{report_id}", response_model=ApiResponse[ReportResponse])
async def get_report(
    report_id: uuid.UUID,
    user: User = Depends(require_permission("reports", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ReportResponse]:
    report = await ReportService(db).require_report(report_id, user.organization_id)
    return ApiResponse(data=serialize_report(report))


@router.patch("/{report_id}", response_model=ApiResponse[ReportResponse])
async def update_report(
    report_id: uuid.UUID,
    payload: UpdateReportRequest,
    user: User = Depends(require_permission("reports", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ReportResponse]:
    service = ReportService(db)
    report = await service.require_report(report_id, user.organization_id)
    report = await service.update(report, payload=payload, actor=user)
    return ApiResponse(data=serialize_report(report), message="Report updated.")


@router.delete("/{report_id}", response_model=ApiResponse[None])
async def delete_report(
    report_id: uuid.UUID,
    user: User = Depends(require_permission("reports", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = ReportService(db)
    report = await service.require_report(report_id, user.organization_id)
    await service.delete(report, actor=user)
    return ApiResponse(message="Report deleted.")


@router.post("/{report_id}/run", response_model=ApiResponse[RunReportResponse])
async def run_report(
    report_id: uuid.UUID,
    # "update", not "read" — running a report is an action with a real side
    # effect (emails recipients), matching the "ai" resource's read-vs-action
    # split (viewing a job vs retrying/approving it).
    user: User = Depends(require_permission("reports", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RunReportResponse]:
    service = ReportService(db)
    report = await service.require_report(report_id, user.organization_id)
    report, row_count, delivered_to = await service.run(report, actor=user)
    return ApiResponse(
        data=RunReportResponse(report=serialize_report(report), row_count=row_count, delivered_to=delivered_to),
        message="Report run." if not delivered_to else f"Report run and emailed to {len(delivered_to)} recipient(s).",
    )
