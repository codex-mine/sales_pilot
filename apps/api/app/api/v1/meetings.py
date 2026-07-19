"""Communication -> Meeting Scheduling routes not scoped to a single Lead
(cross-lead list + actions on an existing meeting by id). Meeting creation
lives on `leads.py` as `/leads/{lead_id}/meetings`, matching how Email
Sending/Generation place their own creation routes under the owning Lead."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.enums import MeetingStatusEnum
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.meeting_serializers import serialize_meeting
from app.schemas.meetings import (
    CancelMeetingRequest,
    LogMeetingOutcomeRequest,
    MeetingResponse,
    ProposeTimesRequest,
    ProposeTimesResponse,
    RescheduleMeetingRequest,
)
from app.services.communication.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])

# NOTE ON ROUTE ORDER: "" (list) is declared before the `/{meeting_id}` family
# below, matching every other router's convention in this codebase.


@router.get("", response_model=ApiResponse[list[MeetingResponse]])
async def list_meetings(
    status_filter: list[str] | None = Query(default=None, alias="status"),
    owner_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[MeetingResponse]]:
    meetings, total = await MeetingService(db).list_for_org(
        user.organization_id, status=status_filter, owner_id=owner_id, date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )
    return ApiResponse(
        data=[serialize_meeting(m) for m in meetings],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/{meeting_id}/propose-times", response_model=ApiResponse[ProposeTimesResponse])
async def propose_meeting_times(
    meeting_id: uuid.UUID,
    payload: ProposeTimesRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProposeTimesResponse]:
    meeting, booking_url = await MeetingService(db).propose_times(
        user.organization_id, meeting_id, slot_count=payload.slot_count, actor=user
    )
    return ApiResponse(
        data=ProposeTimesResponse(meeting=serialize_meeting(meeting), booking_url=booking_url),
        message="Times proposed.",
    )


@router.post("/{meeting_id}/reschedule", response_model=ApiResponse[MeetingResponse])
async def reschedule_meeting(
    meeting_id: uuid.UUID,
    payload: RescheduleMeetingRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MeetingResponse]:
    meeting = await MeetingService(db).reschedule(
        user.organization_id, meeting_id, payload.new_start, payload.new_end, actor=user
    )
    return ApiResponse(data=serialize_meeting(meeting), message="Meeting rescheduled.")


@router.post("/{meeting_id}/cancel", response_model=ApiResponse[MeetingResponse])
async def cancel_meeting(
    meeting_id: uuid.UUID,
    payload: CancelMeetingRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MeetingResponse]:
    meeting = await MeetingService(db).cancel(user.organization_id, meeting_id, actor=user, reason=payload.reason)
    return ApiResponse(data=serialize_meeting(meeting), message="Meeting cancelled.")


@router.post("/{meeting_id}/outcome", response_model=ApiResponse[MeetingResponse])
async def log_meeting_outcome(
    meeting_id: uuid.UUID,
    payload: LogMeetingOutcomeRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MeetingResponse]:
    meeting = await MeetingService(db).log_outcome(
        user.organization_id, meeting_id, MeetingStatusEnum(payload.status), payload.notes, actor=user
    )
    return ApiResponse(data=serialize_meeting(meeting), message="Outcome logged.")
