"""
Celery beat periodic task: internal meeting reminders (Communication ->
Meeting Scheduling & Calendar Booking). Uses the existing Notification model
exactly as the module spec requires — no new table, no "reminded" column on
Meeting. Idempotency (never reminding twice) instead comes from checking
whether a MEETING_REMINDER Notification already exists for a given meeting
before creating another, since the fixed lookback/lookahead window this task
scans will see the same upcoming meeting across several consecutive ticks.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationTypeEnum
from app.models.remaining_domains import Notification
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.notification_repository import NotificationRepository
from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

# How far ahead a meeting must be starting for a reminder to fire. Wider than
# the 15-minute beat interval so a meeting is never skipped by tick timing.
_REMINDER_WINDOW_MINUTES = 60


async def _already_reminded(session: AsyncSession, meeting_id: uuid.UUID) -> bool:
    return (
        await session.scalar(
            select(Notification.id).where(
                Notification.entity_type == "meeting",
                Notification.entity_id == meeting_id,
                Notification.notification_type == NotificationTypeEnum.MEETING_REMINDER.value,
            )
        )
        is not None
    )


@celery_app.task(name="meetings.send_reminders", acks_late=True)
def send_meeting_reminders() -> None:
    async def _run(session: AsyncSession) -> None:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=_REMINDER_WINDOW_MINUTES)
        meetings = await MeetingRepository(session).list_upcoming_for_reminder(now, window_end)
        notifications = NotificationRepository(session)

        for meeting in meetings:
            if meeting.owner_id is None or await _already_reminded(session, meeting.id):
                continue
            lead_name = meeting.lead.full_name if meeting.lead else "your lead"
            await notifications.create(
                organization_id=meeting.organization_id, user_id=meeting.owner_id,
                notification_type=NotificationTypeEnum.MEETING_REMINDER.value,
                title="Upcoming meeting",
                body=f"{meeting.title} with {lead_name} at {meeting.scheduled_start.isoformat()}",
                entity_type="meeting", entity_id=meeting.id, action_url=f"/meetings?meeting={meeting.id}",
            )
        await session.commit()

    asyncio.run(run_with_fresh_session(_run))
