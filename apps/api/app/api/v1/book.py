"""
Public, unauthenticated meeting-booking routes — the prospect-facing half of
Communication -> Meeting Scheduling & Calendar Booking. No route here depends
on `require_permission`/`get_current_user` (see `unsubscribe.py`'s docstring
for why that alone is the entire public-route mechanism in this codebase).

Every route resolves strictly from the signed booking token (`sub` = meeting
id, `organization_id` = tenant) — never a caller-supplied id — and any
resolution failure (bad signature, expired, meeting no longer exists) returns
the same generic "invalid or expired" error so the endpoint never confirms or
denies whether a particular meeting/lead exists.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.meetings import ConfirmBookingRequest, ConfirmBookingResponse, PublicBookingResponse
from app.services.communication.meeting_service import MeetingService

router = APIRouter(prefix="/book", tags=["booking"])


@router.get("/{booking_token}", response_model=ApiResponse[PublicBookingResponse])
async def get_booking(booking_token: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[PublicBookingResponse]:
    data = await MeetingService(db).get_public_booking_data(booking_token)
    return ApiResponse(data=PublicBookingResponse(**data))


@router.post("/{booking_token}/confirm", response_model=ApiResponse[ConfirmBookingResponse])
async def confirm_booking(
    booking_token: str, payload: ConfirmBookingRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[ConfirmBookingResponse]:
    data = await MeetingService(db).confirm_slot(booking_token, start=payload.start, end=payload.end)
    return ApiResponse(data=ConfirmBookingResponse(**data), message="Meeting confirmed.")
