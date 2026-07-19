import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.communication.models import Email


class EmailRepository:
    """Per-Lead outgoing Email rows (Communication domain). The Email
    Generation module only ever creates DRAFT rows on approval —
    transitioning a draft through SCHEDULED/SENDING/SENT/FAILED is the Email
    Sending module's job."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> Email | None:
        return await self.db.scalar(
            select(Email)
            .options(selectinload(Email.events))
            .execution_options(populate_existing=True)
            .where(Email.id == email_id, Email.organization_id == organization_id)
        )

    async def get_by_tracking_pixel_id(self, tracking_pixel_id: str) -> Email | None:
        """No `organization_id` scoping — this is resolved from a public,
        unauthenticated pixel/click request; the tracking_pixel_id itself
        (an unguessable token, generated at send time) IS the tenant
        resolution, exactly like the unsubscribe token's `sub` claim."""
        return await self.db.scalar(select(Email).where(Email.tracking_pixel_id == tracking_pixel_id))

    async def get_by_external_message_id(self, external_message_id: str) -> Email | None:
        """Resolves a webhook payload's message reference back to the Email
        row — also unscoped by organization for the same reason as
        `get_by_tracking_pixel_id` (the caller is the sending provider, not
        an authenticated user)."""
        return await self.db.scalar(select(Email).where(Email.external_message_id == external_message_id))

    async def get_for_update(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> Email | None:
        """Row-locked read for the send path — guards against two concurrent
        requests (or a request racing the scheduler) double-sending the same
        DRAFT/SCHEDULED row."""
        return await self.db.scalar(
            select(Email)
            .where(Email.id == email_id, Email.organization_id == organization_id)
            .with_for_update()
        )

    async def create(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID, **fields: Any) -> Email:
        email = Email(organization_id=organization_id, lead_id=lead_id, **fields)
        self.db.add(email)
        await self.db.flush()
        return email

    async def update(self, email: Email, changes: dict[str, Any], *, updated_by: uuid.UUID | None = None) -> Email:
        for field, value in changes.items():
            setattr(email, field, value)
        email.updated_by = updated_by
        await self.db.flush()
        return email

    async def list_for_lead(
        self, lead_id: uuid.UUID, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[Email]:
        conditions = [Email.lead_id == lead_id, Email.organization_id == organization_id]
        if status:
            conditions.append(Email.current_status == status)
        result = await self.db.scalars(
            select(Email).where(*conditions).order_by(Email.created_at.desc())
        )
        return list(result)

    # ─── Sending: suppression / limits / scheduling ────────────────────────────

    async def get_prior_hard_bounce(self, organization_id: uuid.UUID, to_email: str) -> Email | None:
        """Suppression check: any prior hard-bounced send to this address in
        this organization. `EmailEvent`/webhook processing (Email Tracking
        module) is what actually sets `current_status=BOUNCED` — this only
        reads it."""
        return await self.db.scalar(
            select(Email)
            .where(
                Email.organization_id == organization_id,
                func.lower(Email.to_email) == to_email.lower(),
                Email.current_status == "bounced",
            )
            .order_by(Email.created_at.desc())
            .limit(1)
        )

    async def count_sent_today(self, organization_id: uuid.UUID) -> int:
        """Daily send limit accounting — counts by `sent_at`, not
        `current_status`, so a SENT email that later progresses to
        DELIVERED/OPENED/CLICKED still counts toward the day it was
        actually dispatched."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.db.scalar(
            select(func.count(Email.id)).where(
                Email.organization_id == organization_id,
                Email.sent_at.isnot(None),
                Email.sent_at >= today_start,
            )
        ) or 0

    async def list_due_scheduled(self, *, limit: int = 100) -> list[Email]:
        """The Celery beat scheduler's query, across all organizations —
        `FOR UPDATE SKIP LOCKED` so multiple workers can process the batch
        concurrently without double-sending the same row (see
        `models/ARCHITECTURE.md` §3, same pattern the docs already reserve
        for the CampaignLead scheduler)."""
        now = datetime.now(timezone.utc)
        result = await self.db.scalars(
            select(Email)
            .where(Email.current_status == "scheduled", Email.scheduled_at <= now)
            .order_by(Email.scheduled_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result)

    # ─── Outbox ─────────────────────────────────────────────────────────────────

    async def list_outbox(
        self,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Email], int]:
        conditions = [Email.organization_id == organization_id]
        if status:
            conditions.append(Email.current_status.in_(status))
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(
                or_(func.lower(Email.subject).like(like), func.lower(Email.to_email).like(like))
            )

        total = await self.db.scalar(select(func.count(Email.id)).where(and_(*conditions))) or 0
        result = await self.db.scalars(
            select(Email)
            .options(selectinload(Email.lead))
            .where(and_(*conditions))
            .order_by(Email.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total
