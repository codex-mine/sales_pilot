"""
Hourly aggregation of `EmailEvent` -> pre-aggregated `Metric` rows
(Communication -> Email Tracking analytics). Matches the two-tier
"Event (raw) + Metric (aggregated)" pattern documented in
`models/ARCHITECTURE.md` §7 — dashboards read `Metric` (fast, pre-computed),
never scan `EmailEvent` on every page load.

Idempotent: `Metric` has a UNIQUE(organization_id, campaign_id, metric_name,
metric_date, period) constraint; this task updates the existing hour's row
rather than duplicating it if re-run.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

_PERIOD = "hourly"


async def _compute_and_store(session: AsyncSession, organization_id, campaign_id, since, metric_date) -> None:
    from app.models.enums import EmailEventTypeEnum
    from app.models.remaining_domains import Metric
    from app.repositories.email_event_repository import EmailEventRepository

    counts = await EmailEventRepository(session).aggregate_counts(organization_id, since=since, campaign_id=campaign_id)
    sent = counts.get(EmailEventTypeEnum.SENT.value, 0)
    delivered = counts.get(EmailEventTypeEnum.DELIVERED.value, 0)
    opened = counts.get(EmailEventTypeEnum.OPENED.value, 0)
    clicked = counts.get(EmailEventTypeEnum.CLICKED.value, 0)
    bounced = counts.get(EmailEventTypeEnum.BOUNCED.value, 0)
    denominator = delivered or sent

    values = {
        "email_open_rate": round(opened / denominator, 4) if denominator else 0.0,
        "email_click_rate": round(clicked / denominator, 4) if denominator else 0.0,
        "email_bounce_rate": round(bounced / sent, 4) if sent else 0.0,
    }
    for metric_name, value in values.items():
        existing = await session.scalar(
            select(Metric).where(
                Metric.organization_id == organization_id,
                Metric.campaign_id == campaign_id,
                Metric.metric_name == metric_name,
                Metric.metric_date == metric_date,
                Metric.period == _PERIOD,
            )
        )
        if existing is not None:
            existing.value = value
        else:
            session.add(
                Metric(
                    organization_id=organization_id, campaign_id=campaign_id, metric_name=metric_name,
                    metric_date=metric_date, period=_PERIOD, value=value,
                )
            )
    await session.flush()


async def _run_aggregation(session: AsyncSession) -> None:
    from app.models.identity.models import Organization
    from app.repositories.email_event_repository import EmailEventRepository

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    metric_date = since.replace(minute=0, second=0, microsecond=0)

    org_ids = await session.scalars(select(Organization.id).where(Organization.is_active.is_(True)))
    events_repo = EmailEventRepository(session)
    for organization_id in org_ids:
        await _compute_and_store(session, organization_id, None, since, metric_date)
        for campaign_id in await events_repo.distinct_campaign_ids(organization_id, since=since):
            await _compute_and_store(session, organization_id, campaign_id, since, metric_date)
    await session.commit()


@celery_app.task(name="metrics.aggregate_email_metrics", acks_late=True)
def aggregate_email_metrics_task() -> None:
    asyncio.run(run_with_fresh_session(_run_aggregation))
