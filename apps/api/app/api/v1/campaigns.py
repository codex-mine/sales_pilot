"""
Campaigns -> Multi-Step Sequence Automation routes. Four small routers in one
file (matching prefixes that don't nest under a single parent path):
`campaigns_router` (/campaigns), `sequences_router` (/sequences),
`sequence_steps_router` (/sequence-steps), `campaign_leads_router`
(/campaign-leads) — all registered in `app/api/v1/router.py`.

NOTE ON ROUTE ORDER: within `campaigns_router`, static-string routes
(none needed here beyond the sub-resource paths, which are already more
specific than the bare `/{campaign_id}`) are declared so `/{campaign_id}/...`
sub-paths never get swallowed by a bare `/{campaign_id}` route — same lesson
as every other router in this codebase.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.exceptions.errors import NotFoundError
from app.models.identity.models import User
from app.repositories.campaign_lead_repository import CampaignLeadRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.email_repository import EmailRepository
from app.schemas.campaign_serializers import (
    serialize_campaign,
    serialize_campaign_lead,
    serialize_sequence,
    serialize_sequence_step,
)
from app.schemas.campaigns import (
    BulkEnrollRequest,
    BulkEnrollResponse,
    CampaignCreateRequest,
    CampaignDashboardResponse,
    CampaignFunnelCounts,
    CampaignLeadResponse,
    CampaignResponse,
    CampaignUpdateRequest,
    EnrollByFilterRequest,
    EnrollLeadRequest,
    SequenceCreateRequest,
    SequenceResponse,
    SequenceStepCreateRequest,
    SequenceStepResponse,
    SequenceStepUpdateRequest,
    SequenceUpdateRequest,
)
from app.schemas.common import ApiResponse
from app.services.campaigns.campaign_service import CampaignService
from app.services.campaigns.enrollment_service import EnrollmentService
from app.services.campaigns.sequence_service import SequenceService

campaigns_router = APIRouter(prefix="/campaigns", tags=["campaigns"])
sequences_router = APIRouter(prefix="/sequences", tags=["campaigns"])
sequence_steps_router = APIRouter(prefix="/sequence-steps", tags=["campaigns"])
campaign_leads_router = APIRouter(prefix="/campaign-leads", tags=["campaigns"])


# ─── Campaigns: list / create ────────────────────────────────────────────────────


@campaigns_router.get("", response_model=ApiResponse[list[CampaignResponse]])
async def list_campaigns(
    status_filter: list[str] | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CampaignResponse]]:
    repo = CampaignRepository(db)
    campaigns, total = await repo.list_for_organization(
        user.organization_id, status=status_filter, search=search, page=page, page_size=page_size
    )
    enrolled_counts = await repo.enrolled_counts_for_campaigns([c.id for c in campaigns])
    return ApiResponse(
        data=[serialize_campaign(c, enrolled_count=enrolled_counts.get(c.id, 0)) for c in campaigns],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@campaigns_router.post("", response_model=ApiResponse[CampaignResponse], status_code=201)
async def create_campaign(
    payload: CampaignCreateRequest,
    user: User = Depends(require_permission("campaigns", "create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    campaign = await CampaignService(db).create(organization_id=user.organization_id, payload=payload, actor=user)
    return ApiResponse(data=serialize_campaign(campaign), message="Campaign created.")


# ─── Campaigns: single resource + status control ─────────────────────────────────


@campaigns_router.get("/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def get_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    enrolled_count = await service.campaigns.enrolled_count(campaign_id)
    funnel = await service.campaigns.funnel_counts(campaign_id)
    return ApiResponse(data=serialize_campaign(campaign, enrolled_count=enrolled_count, funnel_counts=funnel))


@campaigns_router.patch("/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    campaign = await service.update(campaign, payload=payload, actor=user)
    return ApiResponse(data=serialize_campaign(campaign), message="Campaign updated.")


@campaigns_router.delete("/{campaign_id}", response_model=ApiResponse[None])
async def delete_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    await service.delete(campaign, actor=user)
    return ApiResponse(message="Campaign deleted.")


@campaigns_router.post("/{campaign_id}/activate", response_model=ApiResponse[CampaignResponse])
async def activate_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    campaign = await service.activate(campaign, actor=user)
    return ApiResponse(data=serialize_campaign(campaign), message="Campaign activated.")


@campaigns_router.post("/{campaign_id}/pause", response_model=ApiResponse[CampaignResponse])
async def pause_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    campaign = await service.pause(campaign, actor=user)
    return ApiResponse(data=serialize_campaign(campaign), message="Campaign paused.")


@campaigns_router.post("/{campaign_id}/archive", response_model=ApiResponse[CampaignResponse])
async def archive_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    campaign = await service.archive(campaign, actor=user)
    return ApiResponse(data=serialize_campaign(campaign), message="Campaign archived.")


# ─── Campaigns: sequences sub-resource ────────────────────────────────────────────


@campaigns_router.get("/{campaign_id}/sequences", response_model=ApiResponse[list[SequenceResponse]])
async def list_campaign_sequences(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SequenceResponse]]:
    sequences = await SequenceService(db).list_for_campaign(campaign_id, user.organization_id)
    return ApiResponse(data=[serialize_sequence(s) for s in sequences])


@campaigns_router.post(
    "/{campaign_id}/sequences", response_model=ApiResponse[SequenceResponse], status_code=201
)
async def create_campaign_sequence(
    campaign_id: uuid.UUID,
    payload: SequenceCreateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SequenceResponse]:
    sequence = await SequenceService(db).create_sequence(campaign_id, user.organization_id, payload=payload, actor=user)
    return ApiResponse(data=serialize_sequence(sequence), message="Sequence created.")


# ─── Campaigns: enrollment ─────────────────────────────────────────────────────────


@campaigns_router.post("/{campaign_id}/enroll", response_model=ApiResponse[CampaignLeadResponse], status_code=201)
async def enroll_lead(
    campaign_id: uuid.UUID,
    payload: EnrollLeadRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignLeadResponse]:
    campaign_lead = await EnrollmentService(db).enroll_lead(
        user.organization_id, campaign_id, payload.lead_id, sequence_id=payload.sequence_id, actor=user
    )
    return ApiResponse(data=serialize_campaign_lead(campaign_lead), message="Lead enrolled.")


@campaigns_router.post("/{campaign_id}/enroll/bulk", response_model=ApiResponse[BulkEnrollResponse])
async def enroll_bulk(
    campaign_id: uuid.UUID,
    payload: BulkEnrollRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkEnrollResponse]:
    result = await EnrollmentService(db).enroll_bulk(
        user.organization_id, campaign_id, payload.lead_ids, sequence_id=payload.sequence_id, actor=user
    )
    return ApiResponse(data=result, message=f"{result.enrolled_count} of {result.requested_count} leads enrolled.")


@campaigns_router.post("/{campaign_id}/enroll/by-filter", response_model=ApiResponse[BulkEnrollResponse])
async def enroll_by_filter(
    campaign_id: uuid.UUID,
    payload: EnrollByFilterRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkEnrollResponse]:
    result = await EnrollmentService(db).enroll_by_filter(user.organization_id, campaign_id, payload, actor=user)
    return ApiResponse(data=result, message=f"{result.enrolled_count} of {result.requested_count} leads enrolled.")


@campaigns_router.get("/{campaign_id}/leads", response_model=ApiResponse[list[CampaignLeadResponse]])
async def list_campaign_leads(
    campaign_id: uuid.UUID,
    status_filter: list[str] | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CampaignLeadResponse]]:
    campaign_leads, total = await CampaignLeadRepository(db).list_for_campaign(
        campaign_id, user.organization_id, status=status_filter, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_campaign_lead(cl) for cl in campaign_leads],
        meta={"page": page, "page_size": page_size, "total": total},
    )


# ─── Campaigns: dashboard ──────────────────────────────────────────────────────────


@campaigns_router.get("/{campaign_id}/dashboard", response_model=ApiResponse[CampaignDashboardResponse])
async def get_campaign_dashboard(
    campaign_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignDashboardResponse]:
    service = CampaignService(db)
    campaign = await service.require_campaign(campaign_id, user.organization_id)
    funnel_counts = await service.campaigns.funnel_counts(campaign_id)
    total_enrolled = sum(funnel_counts.values())
    emails_sent = await EmailRepository(db).count_sent_today_for_campaign(campaign_id)

    funnel = CampaignFunnelCounts(
        enrolled=funnel_counts.get("enrolled", 0), in_progress=funnel_counts.get("in_progress", 0),
        replied=funnel_counts.get("replied", 0), meeting_booked=funnel_counts.get("meeting_booked", 0),
        completed=funnel_counts.get("completed", 0), opted_out=funnel_counts.get("opted_out", 0),
        bounced=funnel_counts.get("bounced", 0),
    )
    open_rate = 0.0
    reply_rate = (funnel.replied / total_enrolled * 100) if total_enrolled else 0.0
    meeting_rate = (funnel.meeting_booked / total_enrolled * 100) if total_enrolled else 0.0

    return ApiResponse(
        data=CampaignDashboardResponse(
            campaign_id=str(campaign.id), status=campaign.status, funnel=funnel,
            total_enrolled=total_enrolled, emails_sent=emails_sent,
            open_rate=round(open_rate, 1), reply_rate=round(reply_rate, 1), meeting_rate=round(meeting_rate, 1),
        )
    )


# ─── Sequences ──────────────────────────────────────────────────────────────────


@sequences_router.patch("/{sequence_id}", response_model=ApiResponse[SequenceResponse])
async def update_sequence(
    sequence_id: uuid.UUID,
    payload: SequenceUpdateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SequenceResponse]:
    service = SequenceService(db)
    sequence = await service.require_sequence(sequence_id, user.organization_id)
    sequence = await service.update_sequence(sequence, payload=payload, actor=user)
    return ApiResponse(data=serialize_sequence(sequence), message="Sequence updated.")


@sequences_router.get("/{sequence_id}/steps", response_model=ApiResponse[list[SequenceStepResponse]])
async def list_sequence_steps(
    sequence_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SequenceStepResponse]]:
    service = SequenceService(db)
    await service.require_sequence(sequence_id, user.organization_id)
    steps = await service.sequences.list_steps(sequence_id, user.organization_id)
    return ApiResponse(data=[serialize_sequence_step(s) for s in steps])


@sequences_router.post(
    "/{sequence_id}/steps", response_model=ApiResponse[SequenceStepResponse], status_code=201
)
async def create_sequence_step(
    sequence_id: uuid.UUID,
    payload: SequenceStepCreateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SequenceStepResponse]:
    step = await SequenceService(db).create_step(sequence_id, user.organization_id, payload=payload, actor=user)
    return ApiResponse(data=serialize_sequence_step(step), message="Step added.")


# ─── Sequence steps ────────────────────────────────────────────────────────────────


@sequence_steps_router.patch("/{step_id}", response_model=ApiResponse[SequenceStepResponse])
async def update_sequence_step(
    step_id: uuid.UUID,
    payload: SequenceStepUpdateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SequenceStepResponse]:
    service = SequenceService(db)
    step = await service.require_step(step_id, user.organization_id)
    step = await service.update_step(step, payload=payload, actor=user)
    return ApiResponse(data=serialize_sequence_step(step), message="Step updated.")


@sequence_steps_router.delete("/{step_id}", response_model=ApiResponse[None])
async def delete_sequence_step(
    step_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = SequenceService(db)
    step = await service.require_step(step_id, user.organization_id)
    await service.delete_step(step, actor=user)
    return ApiResponse(message="Step deleted.")


@sequence_steps_router.post("/{step_id}/move", response_model=ApiResponse[list[SequenceStepResponse]])
async def move_sequence_step(
    step_id: uuid.UUID,
    direction: str = Query(pattern="^(up|down)$"),
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SequenceStepResponse]]:
    service = SequenceService(db)
    step = await service.require_step(step_id, user.organization_id)
    steps = await service.move_step(step, direction=direction, actor=user)  # type: ignore[arg-type]
    return ApiResponse(data=[serialize_sequence_step(s) for s in steps], message="Step reordered.")


# ─── Campaign leads ─────────────────────────────────────────────────────────────────


@campaign_leads_router.delete("/{campaign_lead_id}", response_model=ApiResponse[CampaignLeadResponse])
async def unenroll_campaign_lead(
    campaign_lead_id: uuid.UUID,
    reason: str | None = Query(default=None, max_length=500),
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignLeadResponse]:
    campaign_lead = await EnrollmentService(db).unenroll(
        user.organization_id, campaign_lead_id, reason=reason, actor=user
    )
    return ApiResponse(data=serialize_campaign_lead(campaign_lead), message="Lead unenrolled.")


@campaign_leads_router.get("/{campaign_lead_id}", response_model=ApiResponse[CampaignLeadResponse])
async def get_campaign_lead(
    campaign_lead_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CampaignLeadResponse]:
    campaign_lead = await CampaignLeadRepository(db).get_by_id(campaign_lead_id, user.organization_id)
    if campaign_lead is None:
        raise NotFoundError("Enrollment not found.")
    return ApiResponse(data=serialize_campaign_lead(campaign_lead))
