"""ORM -> response-schema mapping for the Email Tracking module."""

from app.models.communication.models import EmailEvent
from app.schemas.email_serializers import _ev
from app.schemas.email_tracking import EmailEventResponse, EmailTimelineResponse


def serialize_email_event(event: EmailEvent) -> EmailEventResponse:
    return EmailEventResponse(
        id=str(event.id),
        email_id=str(event.email_id),
        event_type=_ev(event.event_type),
        occurred_at=event.occurred_at,
        provider=event.provider,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        click_url=event.click_url,
        bounce_reason=event.bounce_reason,
        metadata=event.metadata_,
    )


def serialize_email_timeline(email_id: str, current_status: str, events: list[EmailEvent]) -> EmailTimelineResponse:
    return EmailTimelineResponse(
        email_id=email_id,
        current_status=_ev(current_status),
        events=[serialize_email_event(e) for e in events],
    )
