"""ORM -> response-schema mapping for the Meeting Scheduling module."""

from app.models.communication.models import Meeting
from app.schemas.email_serializers import _ev
from app.schemas.meetings import CalendarEventResponse, MeetingOwnerResponse, MeetingResponse


def serialize_meeting(meeting: Meeting) -> MeetingResponse:
    lead = meeting.lead
    return MeetingResponse(
        id=str(meeting.id),
        organization_id=str(meeting.organization_id),
        lead_id=str(meeting.lead_id),
        lead_full_name=lead.full_name if lead else None,
        lead_company_name=lead.company_name if lead else None,
        owner=(
            MeetingOwnerResponse(id=str(meeting.owner.id), full_name=meeting.owner.full_name, email=meeting.owner.email)
            if meeting.owner
            else None
        ),
        title=meeting.title,
        description=meeting.description,
        status=_ev(meeting.status),
        proposed_times=meeting.proposed_times or [],
        scheduled_start=meeting.scheduled_start,
        scheduled_end=meeting.scheduled_end,
        duration_minutes=meeting.duration_minutes,
        meeting_url=meeting.meeting_url,
        notes=meeting.notes,
        confirmed_at=meeting.confirmed_at,
        cancelled_at=meeting.cancelled_at,
        completed_at=meeting.completed_at,
        calendar_event=(
            CalendarEventResponse(
                id=str(meeting.calendar_event.id), provider=meeting.calendar_event.provider,
                meet_link=meeting.calendar_event.meet_link, is_synced=meeting.calendar_event.is_synced,
            )
            if meeting.calendar_event
            else None
        ),
        created_at=meeting.created_at,
    )
