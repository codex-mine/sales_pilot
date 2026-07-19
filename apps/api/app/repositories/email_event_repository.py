import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication.models import EmailEvent


class EmailEventRepository:
    """Append-only `EmailEvent` rows — the canonical delivery/engagement
    history. Every insert path here must be idempotency-safe: webhook
    providers redeliver aggressively, and a tracking pixel can fire more
    than once per real human open."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_provider_event_id(self, provider_event_id: str) -> EmailEvent | None:
        return await self.db.scalar(select(EmailEvent).where(EmailEvent.provider_event_id == provider_event_id))

    async def create(self, *, organization_id: uuid.UUID, email_id: uuid.UUID, event_type: str, **fields: Any) -> EmailEvent:
        event = EmailEvent(organization_id=organization_id, email_id=email_id, event_type=event_type, **fields)
        self.db.add(event)
        await self.db.flush()
        return event

    async def create_idempotent_by_provider_event_id(
        self, *, organization_id: uuid.UUID, email_id: uuid.UUID, event_type: str, provider_event_id: str, **fields: Any
    ) -> tuple[EmailEvent, bool]:
        """Returns (event, was_created). A duplicate `provider_event_id` is a
        successful no-op that returns the original row, per the module's
        upsert-or-ignore requirement — webhook redelivery must never
        double-insert."""
        existing = await self.get_by_provider_event_id(provider_event_id)
        if existing is not None:
            return existing, False
        try:
            async with self.db.begin_nested():
                event = EmailEvent(
                    organization_id=organization_id, email_id=email_id, event_type=event_type,
                    provider_event_id=provider_event_id, **fields,
                )
                self.db.add(event)
                await self.db.flush()
            return event, True
        except IntegrityError:
            # Lost the race to a concurrent delivery of the same webhook.
            existing = await self.get_by_provider_event_id(provider_event_id)
            if existing is None:
                raise
            return existing, False

    async def get_recent_open(self, email_id: uuid.UUID, since: datetime) -> EmailEvent | None:
        """Open-pixel dedupe: pixel fires have no provider-assigned id, so
        idempotency here is a rolling time window per email instead."""
        return await self.db.scalar(
            select(EmailEvent)
            .where(EmailEvent.email_id == email_id, EmailEvent.event_type == "opened", EmailEvent.occurred_at >= since)
            .order_by(EmailEvent.occurred_at.desc())
            .limit(1)
        )

    async def list_for_email(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> list[EmailEvent]:
        result = await self.db.scalars(
            select(EmailEvent)
            .where(EmailEvent.email_id == email_id, EmailEvent.organization_id == organization_id)
            .order_by(EmailEvent.occurred_at)
        )
        return list(result)

    async def get_latest_reasons(
        self, email_ids: list[uuid.UUID], *, event_types: tuple[str, ...] = ("bounced", "complained")
    ) -> dict[uuid.UUID, str]:
        """One batched query for the Outbox list — the most recent
        bounce/complaint reason per email, avoiding an N+1 per row. Complaint
        events don't carry a `bounce_reason`, so those rows fall back to a
        fixed "Marked as spam" label the caller doesn't need to special-case."""
        if not email_ids:
            return {}
        result = await self.db.scalars(
            select(EmailEvent)
            .where(EmailEvent.email_id.in_(email_ids), EmailEvent.event_type.in_(event_types))
            .order_by(EmailEvent.email_id, EmailEvent.occurred_at.desc())
        )
        reasons: dict[uuid.UUID, str] = {}
        for event in result:
            if event.email_id in reasons:
                continue  # already have the latest (first seen per email_id, due to the ORDER BY)
            reasons[event.email_id] = event.bounce_reason or ("Marked as spam" if event.event_type == "complained" else "Bounced")
        return reasons

    async def aggregate_counts(
        self, organization_id: uuid.UUID, *, since: datetime, campaign_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        """Per-event-type counts for the metrics aggregation task. Joins
        through `Email` -> `CampaignLead` only when scoping to a specific
        campaign, since `EmailEvent` doesn't carry `campaign_id` itself."""
        from app.models.campaigns.models import CampaignLead
        from app.models.communication.models import Email

        conditions = [EmailEvent.organization_id == organization_id, EmailEvent.occurred_at >= since]
        query = select(EmailEvent.event_type, func.count(EmailEvent.id))
        if campaign_id is not None:
            query = (
                query.join(Email, Email.id == EmailEvent.email_id)
                .join(CampaignLead, CampaignLead.id == Email.campaign_lead_id)
            )
            conditions.append(CampaignLead.campaign_id == campaign_id)
        query = query.where(and_(*conditions)).group_by(EmailEvent.event_type)
        rows = await self.db.execute(query)
        return {event_type: count for event_type, count in rows.all()}

    async def daily_counts(self, organization_id: uuid.UUID, *, since: datetime) -> dict[Any, dict[str, int]]:
        """Per-day, per-event-type counts for the performance analytics
        endpoint's "over time" chart — reads raw `EmailEvent` rather than
        the hourly-aggregated `Metric` table so the chart has data from day
        one, before the metrics task has had a chance to backfill history."""
        # A single reused labeled expression, not three separate
        # `func.date_trunc(...)` calls — each call binds its own "day"
        # parameter, and Postgres then can't tell the SELECT/GROUP BY/
        # ORDER BY expressions are identical (asyncpg.GroupingError).
        day_bucket = func.date_trunc("day", EmailEvent.occurred_at).label("day_bucket")
        query = (
            select(day_bucket, EmailEvent.event_type, func.count(EmailEvent.id))
            .where(EmailEvent.organization_id == organization_id, EmailEvent.occurred_at >= since)
            .group_by(day_bucket, EmailEvent.event_type)
            .order_by(day_bucket)
        )
        rows = await self.db.execute(query)
        by_day: dict[Any, dict[str, int]] = {}
        for day, event_type, count in rows.all():
            by_day.setdefault(day, {})[event_type] = count
        return by_day

    async def distinct_campaign_ids(self, organization_id: uuid.UUID, *, since: datetime) -> list[uuid.UUID]:
        """Which campaigns had email activity in the window — drives the
        metrics task's per-campaign aggregation loop."""
        from app.models.campaigns.models import CampaignLead
        from app.models.communication.models import Email

        result = await self.db.scalars(
            select(CampaignLead.campaign_id)
            .join(Email, Email.campaign_lead_id == CampaignLead.id)
            .join(EmailEvent, EmailEvent.email_id == Email.id)
            .where(EmailEvent.organization_id == organization_id, EmailEvent.occurred_at >= since)
            .distinct()
        )
        return list(result)
