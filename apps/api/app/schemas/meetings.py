"""Request/response schemas for Communication -> Meeting Scheduling & Calendar
Booking, plus the personal Google Calendar connection (Settings -> Calendar
Integration)."""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Calendar integration ───────────────────────────────────────────────────────


class CalendarConnectionStatusResponse(BaseModel):
    is_connected: bool
    account_email: str | None
    connected_at: datetime | None


# ─── Meetings ────────────────────────────────────────────────────────────────────


class ProposedSlot(BaseModel):
    start: datetime
    end: datetime


class MeetingOwnerResponse(BaseModel):
    id: str
    full_name: str
    email: str


class CalendarEventResponse(BaseModel):
    id: str
    provider: str
    meet_link: str | None
    html_link: str | None = None
    is_synced: bool


class MeetingResponse(BaseModel):
    id: str
    organization_id: str
    lead_id: str
    lead_full_name: str | None = None
    lead_company_name: str | None = None
    owner: MeetingOwnerResponse | None
    title: str
    description: str | None
    status: str
    proposed_times: list[ProposedSlot]
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    duration_minutes: int
    meeting_url: str | None
    notes: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    calendar_event: CalendarEventResponse | None
    created_at: datetime


class CreateMeetingRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=5000)
    duration_minutes: int = Field(default=30, ge=15, le=480)
    owner_id: str | None = None
    source_message_id: str | None = None


class ProposeTimesRequest(BaseModel):
    slot_count: int = Field(default=5, ge=1, le=20)


class ProposeTimesResponse(BaseModel):
    meeting: MeetingResponse
    booking_url: str


class RescheduleMeetingRequest(BaseModel):
    new_start: datetime
    new_end: datetime


class CancelMeetingRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class LogMeetingOutcomeRequest(BaseModel):
    status: str = Field(pattern="^(completed|no_show)$")
    notes: str | None = Field(default=None, max_length=5000)


# ─── Public booking page ────────────────────────────────────────────────────────


class PublicBookingResponse(BaseModel):
    """Deliberately minimal — no lead/organization internal ids, only what a
    prospect needs to pick a time."""

    status: str
    organization_name: str
    host_name: str | None
    title: str
    description: str | None
    duration_minutes: int
    proposed_times: list[ProposedSlot]
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    meeting_url: str | None


class ConfirmBookingRequest(BaseModel):
    start: datetime
    end: datetime


class ConfirmBookingResponse(BaseModel):
    organization_name: str
    host_name: str | None
    title: str
    scheduled_start: datetime
    scheduled_end: datetime
    meeting_url: str | None
