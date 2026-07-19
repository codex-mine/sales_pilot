"""
Communication -> Meeting Scheduling & Calendar Booking.

Honors the Meeting/CalendarEvent split documented on the models exactly:
creating a Meeting (status=PROPOSED) never touches Google Calendar; only
`confirm_slot` creates the CalendarEvent and calls the provider. There is no
transient "confirming" status — the external `create_event` call always runs
BEFORE any Meeting/CalendarEvent row is written, so a provider failure simply
raises before touching the DB and the Meeting is left exactly as it was
(PROPOSED), never CONFIRMED without a linked CalendarEvent.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import (
    CalendarNotConnectedError,
    NotFoundError,
    SlotUnavailableError,
    ValidationError,
)
from app.models.communication.models import Meeting
from app.models.enums import ActivityTypeEnum, AuditActionEnum, LeadStatusEnum, MeetingStatusEnum, NotificationTypeEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.calendar_event_repository import CalendarEventRepository
from app.repositories.integration_repository import IntegrationRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.leads import LeadUpdateRequest
from app.security.tokens import create_booking_token, decode_token
from app.services.calendar.calendar_client import get_calendar_client
from app.services.calendar.calendar_integration_service import INTEGRATION_TYPE as CALENDAR_INTEGRATION_TYPE
from app.services.calendar.slot_planner import generate_candidate_slots, is_slot_busy
from app.services.lead_service import LeadService
from app.services.lead_status_resolver import next_lead_status
from app.services.system_actor import resolve_org_owner

_TERMINAL_OUTCOME_STATUSES = {MeetingStatusEnum.COMPLETED, MeetingStatusEnum.NO_SHOW}


class MeetingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.meetings = MeetingRepository(db)
        self.calendar_events = CalendarEventRepository(db)
        self.integrations = IntegrationRepository(db)
        self.leads = LeadRepository(db)
        self.organizations = OrganizationRepository(db)
        self.lead_service = LeadService(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.notifications = NotificationRepository(db)

    # ─── Reads ──────────────────────────────────────────────────────────────────

    async def require_meeting(self, meeting_id: uuid.UUID, organization_id: uuid.UUID) -> Meeting:
        meeting = await self.meetings.get_by_id(meeting_id, organization_id)
        if meeting is None:
            raise NotFoundError("Meeting not found.")
        return meeting

    async def list_for_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> list[Meeting]:
        await self.lead_service.require_lead(lead_id, organization_id)
        return await self.meetings.list_for_lead(lead_id, organization_id)

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None,
        owner_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Meeting], int]:
        return await self.meetings.list_for_org(
            organization_id, status=status, owner_id=owner_id, date_from=date_from, date_to=date_to,
            page=page, page_size=page_size,
        )

    # ─── Create + propose ───────────────────────────────────────────────────────

    async def create_meeting(
        self,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
        owner_id: uuid.UUID,
        title: str,
        duration_minutes: int,
        *,
        actor: User,
        description: str | None = None,
        source_message_id: uuid.UUID | None = None,
    ) -> Meeting:
        lead = await self.lead_service.require_lead(lead_id, organization_id)
        notes = f"Created from inbound reply {source_message_id}." if source_message_id else None
        meeting = await self.meetings.create(
            organization_id=organization_id, lead_id=lead_id, owner_id=owner_id,
            title=title, description=description, duration_minutes=duration_minutes,
            status=MeetingStatusEnum.PROPOSED.value, notes=notes,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_created", "lead_id": str(lead.id), "title": title},
        )
        await self.db.commit()
        return await self.require_meeting(meeting.id, organization_id)

    async def propose_times(
        self, organization_id: uuid.UUID, meeting_id: uuid.UUID, *, slot_count: int, actor: User
    ) -> tuple[Meeting, str]:
        meeting = await self.require_meeting(meeting_id, organization_id)
        if meeting.status != MeetingStatusEnum.PROPOSED.value:
            raise ValidationError("Only a proposed meeting can have times proposed.")
        if meeting.owner_id is None:
            raise ValidationError("This meeting has no owner — assign one before proposing times.")

        integration = await self._require_owner_integration(organization_id, meeting.owner_id)
        settings = get_settings()
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(days=settings.meeting_proposal_window_days + 1)

        client = get_calendar_client(CALENDAR_INTEGRATION_TYPE, self.db)
        busy_blocks = await client.get_freebusy(integration, now, window_end)
        candidates = generate_candidate_slots(
            busy_blocks, now=now, duration_minutes=meeting.duration_minutes, slot_count=slot_count,
            window_days=settings.meeting_proposal_window_days,
            business_start_hour=settings.meeting_business_hours_start,
            business_end_hour=settings.meeting_business_hours_end,
        )
        if not candidates:
            raise ValidationError("No open slots were found in the owner's calendar over the proposal window.")

        proposed_times = [{"start": slot["start"].isoformat(), "end": slot["end"].isoformat()} for slot in candidates]
        meeting = await self.meetings.update(meeting, {"proposed_times": proposed_times})

        booking_token = create_booking_token(str(meeting.id), str(organization_id))
        booking_url = f"{settings.frontend_url}/book/{booking_token}"

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_times_proposed", "slot_count": len(proposed_times)},
        )
        await self.db.commit()
        meeting = await self.require_meeting(meeting.id, organization_id)
        return meeting, booking_url

    async def _require_owner_integration(self, organization_id: uuid.UUID, owner_id: uuid.UUID):
        integration = await self.integrations.get_user_level(organization_id, owner_id, CALENDAR_INTEGRATION_TYPE)
        if integration is None or not integration.is_active or not integration.refresh_token_encrypted:
            raise CalendarNotConnectedError()
        return integration

    # ─── Public booking ─────────────────────────────────────────────────────────

    @staticmethod
    def _decode_booking_token(booking_token: str) -> tuple[uuid.UUID, uuid.UUID]:
        try:
            payload = decode_token(booking_token, expected_type="booking")
            return uuid.UUID(payload["sub"]), uuid.UUID(payload["organization_id"])
        except Exception as exc:  # noqa: BLE001 — never leak *why* a token failed
            raise NotFoundError("This booking link is invalid or has expired.") from exc

    async def get_public_booking_data(self, booking_token: str) -> dict:
        meeting_id, organization_id = self._decode_booking_token(booking_token)
        meeting = await self.meetings.get_for_booking(meeting_id, organization_id)
        if meeting is None:
            raise NotFoundError("This booking link is invalid or has expired.")

        organization = await self.organizations.get_by_id(organization_id)
        return {
            "status": meeting.status,
            "organization_name": organization.name if organization else "",
            "host_name": meeting.owner.full_name if meeting.owner else None,
            "title": meeting.title,
            "description": meeting.description,
            "duration_minutes": meeting.duration_minutes,
            "proposed_times": meeting.proposed_times or [],
            "scheduled_start": meeting.scheduled_start,
            "scheduled_end": meeting.scheduled_end,
            "meeting_url": meeting.meeting_url,
        }

    async def confirm_slot(self, booking_token: str, *, start: datetime, end: datetime) -> dict:
        meeting_id, organization_id = self._decode_booking_token(booking_token)
        meeting = await self.meetings.get_for_booking(meeting_id, organization_id)
        if meeting is None:
            raise NotFoundError("This booking link is invalid or has expired.")
        if meeting.status != MeetingStatusEnum.PROPOSED.value:
            raise ValidationError("This meeting is no longer open for booking.")
        if meeting.owner_id is None:
            raise ValidationError("This meeting has no owner and cannot be confirmed.")

        chosen = self._match_proposed_slot(meeting, start, end)
        if chosen is None:
            raise SlotUnavailableError("That time was not one of the proposed slots.")

        integration = await self._require_owner_integration(organization_id, meeting.owner_id)
        client = get_calendar_client(CALENDAR_INTEGRATION_TYPE, self.db)

        # Re-validate at confirm time — the owner's calendar may have
        # changed since the slots were proposed.
        busy_blocks = await client.get_freebusy(integration, chosen[0], chosen[1])
        if is_slot_busy(chosen[0], chosen[1], busy_blocks):
            raise SlotUnavailableError()

        lead = await self.leads.get_by_id(meeting.lead_id, organization_id)
        attendee_emails = [lead.email] if lead and lead.email else []

        # The external call happens BEFORE any DB write for confirmation —
        # if it raises, execution stops here and the Meeting is untouched.
        result = await client.create_event(
            integration, title=meeting.title, description=meeting.description,
            start=chosen[0], end=chosen[1], attendee_emails=attendee_emails,
        )

        calendar_event = await self.calendar_events.create(
            organization_id=organization_id, user_id=meeting.owner_id, integration_id=integration.id,
            provider=CALENDAR_INTEGRATION_TYPE, provider_event_id=result.provider_event_id,
            provider_calendar_id=result.provider_calendar_id, title=meeting.title,
            start_time=chosen[0], end_time=chosen[1], meet_link=result.meet_link,
            attendees=attendee_emails, is_synced=True, last_synced_at=datetime.now(timezone.utc),
        )
        meeting = await self.meetings.update(
            meeting,
            {
                "calendar_event_id": calendar_event.id, "status": MeetingStatusEnum.CONFIRMED.value,
                "scheduled_start": chosen[0], "scheduled_end": chosen[1],
                "confirmed_at": datetime.now(timezone.utc), "meeting_url": result.meet_link,
            },
        )

        actor = await resolve_org_owner(self.db, organization_id)
        if lead is not None:
            new_status = next_lead_status(lead.status, LeadStatusEnum.DEMO_SCHEDULED)
            if new_status != lead.status:
                await self.lead_service.update(lead, payload=LeadUpdateRequest(status=new_status), actor=actor)
            await self.activities.record(
                organization_id=organization_id, lead_id=lead.id, actor_id=None,
                activity_type=ActivityTypeEnum.MEETING_SCHEDULED,
                summary=f"Meeting confirmed with {lead.full_name} for {chosen[0].isoformat()}.",
            )
        if meeting.owner_id:
            await self.notifications.create(
                organization_id=organization_id, user_id=meeting.owner_id,
                notification_type=NotificationTypeEnum.MEETING_BOOKED.value,
                title="Meeting booked", body=f"{meeting.title} — {chosen[0].isoformat()}",
                entity_type="meeting", entity_id=meeting.id, action_url=f"/meetings?meeting={meeting.id}",
            )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.UPDATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_confirmed", "start": chosen[0].isoformat()},
        )
        await self.db.commit()
        meeting = await self.require_meeting(meeting.id, organization_id)
        organization = await self.organizations.get_by_id(organization_id)
        return {
            "organization_name": organization.name if organization else "",
            "host_name": meeting.owner.full_name if meeting.owner else None,
            "title": meeting.title,
            "scheduled_start": meeting.scheduled_start,
            "scheduled_end": meeting.scheduled_end,
            "meeting_url": meeting.meeting_url,
        }

    @staticmethod
    def _match_proposed_slot(meeting: Meeting, start: datetime, end: datetime) -> tuple[datetime, datetime] | None:
        for entry in meeting.proposed_times or []:
            entry_start = datetime.fromisoformat(entry["start"])
            entry_end = datetime.fromisoformat(entry["end"])
            if entry_start == start and entry_end == end:
                return entry_start, entry_end
        return None

    # ─── Reschedule / cancel ────────────────────────────────────────────────────

    async def reschedule(
        self, organization_id: uuid.UUID, meeting_id: uuid.UUID, new_start: datetime, new_end: datetime, *, actor: User
    ) -> Meeting:
        meeting = await self.require_meeting(meeting_id, organization_id)
        if meeting.status != MeetingStatusEnum.CONFIRMED.value:
            raise ValidationError("Only a confirmed meeting can be rescheduled.")
        if new_end <= new_start:
            raise ValidationError("End time must be after start time.")

        if meeting.calendar_event is not None and meeting.owner_id is not None:
            integration = await self._require_owner_integration(organization_id, meeting.owner_id)
            client = get_calendar_client(CALENDAR_INTEGRATION_TYPE, self.db)
            result = await client.update_event(
                integration, provider_event_id=meeting.calendar_event.provider_event_id, start=new_start, end=new_end,
            )
            await self.calendar_events.update(
                meeting.calendar_event,
                {"start_time": new_start, "end_time": new_end, "last_synced_at": datetime.now(timezone.utc)},
            )
            meeting_url = result.meet_link or meeting.meeting_url
        else:
            meeting_url = meeting.meeting_url

        meeting = await self.meetings.update(
            meeting, {"scheduled_start": new_start, "scheduled_end": new_end, "meeting_url": meeting_url}
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_rescheduled", "new_start": new_start.isoformat()},
        )
        await self.db.commit()
        return await self.require_meeting(meeting.id, organization_id)

    async def cancel(
        self, organization_id: uuid.UUID, meeting_id: uuid.UUID, *, actor: User, reason: str | None = None
    ) -> Meeting:
        meeting = await self.require_meeting(meeting_id, organization_id)
        if meeting.status in (MeetingStatusEnum.CANCELLED.value, *[s.value for s in _TERMINAL_OUTCOME_STATUSES]):
            raise ValidationError("This meeting cannot be cancelled from its current state.")

        if meeting.calendar_event is not None and meeting.owner_id is not None:
            integration = await self._require_owner_integration(organization_id, meeting.owner_id)
            client = get_calendar_client(CALENDAR_INTEGRATION_TYPE, self.db)
            await client.delete_event(integration, provider_event_id=meeting.calendar_event.provider_event_id)
            await self.calendar_events.update(meeting.calendar_event, {"is_synced": False})

        notes = f"{meeting.notes}\nCancelled: {reason}" if meeting.notes and reason else (reason or meeting.notes)
        meeting = await self.meetings.update(
            meeting, {"status": MeetingStatusEnum.CANCELLED.value, "cancelled_at": datetime.now(timezone.utc), "notes": notes}
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_cancelled", "reason": reason},
        )
        await self.db.commit()
        return await self.require_meeting(meeting.id, organization_id)

    # ─── Outcome ─────────────────────────────────────────────────────────────────

    async def log_outcome(
        self, organization_id: uuid.UUID, meeting_id: uuid.UUID, status: MeetingStatusEnum, notes: str | None, *, actor: User
    ) -> Meeting:
        if status not in _TERMINAL_OUTCOME_STATUSES:
            raise ValidationError("Outcome must be 'completed' or 'no_show'.")
        meeting = await self.require_meeting(meeting_id, organization_id)
        if meeting.status != MeetingStatusEnum.CONFIRMED.value:
            raise ValidationError("Only a confirmed meeting can have an outcome logged.")

        combined_notes = f"{meeting.notes}\n{notes}" if meeting.notes and notes else (notes or meeting.notes)
        meeting = await self.meetings.update(
            meeting, {"status": status.value, "completed_at": datetime.now(timezone.utc), "notes": combined_notes}
        )

        if status == MeetingStatusEnum.COMPLETED:
            await self.activities.record(
                organization_id=organization_id, lead_id=meeting.lead_id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.MEETING_COMPLETED,
                summary=f"Meeting '{meeting.title}' marked completed.",
            )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="meeting", resource_id=meeting.id,
            changes={"event": "meeting_outcome_logged", "status": status.value},
        )
        await self.db.commit()
        return await self.require_meeting(meeting.id, organization_id)
