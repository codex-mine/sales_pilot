import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.communication.models import Meeting
from app.models.enums import MeetingStatusEnum


class MeetingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, meeting_id: uuid.UUID, organization_id: uuid.UUID) -> Meeting | None:
        return await self.db.scalar(
            select(Meeting)
            .options(selectinload(Meeting.lead), selectinload(Meeting.owner), selectinload(Meeting.calendar_event))
            .where(Meeting.id == meeting_id, Meeting.organization_id == organization_id)
        )

    async def get_for_booking(self, meeting_id: uuid.UUID, organization_id: uuid.UUID) -> Meeting | None:
        """Resolved from a signed booking token's `sub`/`organization_id`
        claims (never a caller-supplied id directly) — the public booking
        page's only entry point into a Meeting row."""
        return await self.get_by_id(meeting_id, organization_id)

    async def list_for_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> list[Meeting]:
        result = await self.db.scalars(
            select(Meeting)
            .options(selectinload(Meeting.lead), selectinload(Meeting.owner), selectinload(Meeting.calendar_event))
            .where(Meeting.organization_id == organization_id, Meeting.lead_id == lead_id)
            .order_by(Meeting.created_at.desc())
        )
        return list(result)

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None = None,
        owner_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Meeting], int]:
        conditions = [Meeting.organization_id == organization_id]
        if status:
            conditions.append(Meeting.status.in_(status))
        if owner_id:
            conditions.append(Meeting.owner_id == owner_id)
        if date_from:
            conditions.append(Meeting.scheduled_start >= date_from)
        if date_to:
            conditions.append(Meeting.scheduled_start <= date_to)

        base = select(Meeting).where(and_(*conditions))
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.options(selectinload(Meeting.lead), selectinload(Meeting.owner), selectinload(Meeting.calendar_event))
            .order_by(Meeting.scheduled_start.asc().nullslast(), Meeting.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total

    async def status_distribution(self, organization_id: uuid.UUID) -> dict[str, int]:
        """Live `Meeting.status` GROUP BY for the module 12 nightly aggregation
        task's meeting-funnel Metric rows — small, indexed table, cheap even
        unaggregated (same exception as `LeadRepository.status_distribution`)."""
        rows = await self.db.execute(
            select(Meeting.status, func.count(Meeting.id))
            .where(Meeting.organization_id == organization_id)
            .group_by(Meeting.status)
        )
        return {status: count for status, count in rows.all()}

    async def list_upcoming_for_reminder(self, window_start: datetime, window_end: datetime) -> list[Meeting]:
        """Confirmed meetings starting within the reminder window — used by
        the Celery beat reminder task. Idempotency (never reminding twice)
        is enforced by the caller checking for an existing Notification, not
        here, since Meeting has no dedicated "reminded" column."""
        result = await self.db.scalars(
            select(Meeting)
            .options(selectinload(Meeting.lead), selectinload(Meeting.owner))
            .where(
                Meeting.status == MeetingStatusEnum.CONFIRMED.value,
                Meeting.scheduled_start.is_not(None),
                Meeting.scheduled_start >= window_start,
                Meeting.scheduled_start <= window_end,
            )
        )
        return list(result)

    async def create(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID, **fields: Any) -> Meeting:
        meeting = Meeting(organization_id=organization_id, lead_id=lead_id, **fields)
        self.db.add(meeting)
        await self.db.flush()
        return meeting

    async def update(self, meeting: Meeting, changes: dict[str, Any]) -> Meeting:
        for field, value in changes.items():
            setattr(meeting, field, value)
        await self.db.flush()
        return meeting
