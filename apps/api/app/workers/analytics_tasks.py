"""
Module 12 -> nightly Metric aggregation + scheduled report delivery.

**Cadence decision**: daily only, not an additional hourly pass. The two
widgets that actually benefit from same-day freshness (Pipeline Funnel,
Meeting status) read `Lead`/`Meeting` live instead of `Metric` (see
`dashboard_service.py`'s docstring) — that already solves the "today" problem
for the widgets a sales leader checks most. AI cost, campaign performance, and
meeting-count trend are "how are we doing this month" numbers a 24h lag is
fine for, so one daily pass (`aggregate_daily_metrics`, run once at 01:00 UTC)
is enough for V1, avoiding an over-built second beat schedule.

**Snapshot vs delta**: `lead_funnel`/`campaign_funnel`/`meetings` are current-
state *snapshots* taken at task-run time (Lead/CampaignLead/Meeting have no
historical status log to reconstruct "as of midnight" from) — each day's row
is "what the distribution looked like this morning," which still charts a
meaningful trend over time even though it isn't a true daily delta. `ai_cost`/
`ai_job_count`/`ai_tokens` ARE true deltas: the trailing 24h window of `AIJob`
rows ending at task-run time, since `AIJob.created_at` supports it. All rows
for a given run share `metric_date = start of the day the task runs`, so a
re-run the same day upserts in place (see `MetricRepository.upsert`).

`check_scheduled_reports` runs hourly and is the "simpler per-Report cron
check" the module 12 spec explicitly allows in place of a full `ScheduledJob`
polling loop + cron-expression parser: no `croniter` dependency exists in this
project, so `Report.schedule_cron` stores one of `"daily"|"weekly"|"monthly"`
(validated in `app/schemas/analytics.py`) rather than real cron syntax, and
"due" is a simple elapsed-time-since-`last_run_at` check.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

_PERIOD = "daily"
_DUE_BUFFER = {
    "daily": timedelta(hours=23),
    "weekly": timedelta(days=6, hours=23),
    "monthly": timedelta(days=27),
}


async def _aggregate_for_organization(session: AsyncSession, organization_id: uuid.UUID, *, now: datetime, day_start: datetime) -> None:
    from app.models.campaigns.models import CampaignLead
    from app.models.enums import LeadStatusEnum
    from app.repositories.ai_job_repository import AIJobRepository
    from app.repositories.campaign_lead_repository import CampaignLeadRepository
    from app.repositories.campaign_repository import CampaignRepository
    from app.repositories.lead_repository import LeadRepository
    from app.repositories.meeting_repository import MeetingRepository
    from app.repositories.metric_repository import MetricRepository

    metrics = MetricRepository(session)

    # Lead pipeline funnel (snapshot).
    lead_counts = await LeadRepository(session).status_distribution(organization_id)
    for status in LeadStatusEnum:
        await metrics.upsert(
            organization_id=organization_id, campaign_id=None, metric_name=f"lead_funnel__{status.value}",
            metric_date=day_start, period=_PERIOD, value=lead_counts.get(status.value, 0),
            dimensions={"status": status.value},
        )

    # AI cost/usage (trailing-24h delta), per job_type + org-wide totals.
    since = now - timedelta(hours=24)
    usage = await AIJobRepository(session).usage_summary_for_window(organization_id, start=since)
    total_cost = total_jobs = total_tokens = 0.0
    for row in usage:
        job_type = row["job_type"]
        await metrics.upsert(
            organization_id=organization_id, campaign_id=None, metric_name=f"ai_cost__{job_type}",
            metric_date=day_start, period=_PERIOD, value=row["cost_usd"], dimensions={"job_type": job_type},
        )
        await metrics.upsert(
            organization_id=organization_id, campaign_id=None, metric_name=f"ai_job_count__{job_type}",
            metric_date=day_start, period=_PERIOD, value=row["job_count"], dimensions={"job_type": job_type},
        )
        await metrics.upsert(
            organization_id=organization_id, campaign_id=None, metric_name=f"ai_tokens__{job_type}",
            metric_date=day_start, period=_PERIOD, value=row["total_tokens"], dimensions={"job_type": job_type},
        )
        total_cost += row["cost_usd"]
        total_jobs += row["job_count"]
        total_tokens += row["total_tokens"]
    await metrics.upsert(organization_id=organization_id, campaign_id=None, metric_name="ai_cost_total", metric_date=day_start, period=_PERIOD, value=total_cost)
    await metrics.upsert(organization_id=organization_id, campaign_id=None, metric_name="ai_job_count_total", metric_date=day_start, period=_PERIOD, value=total_jobs)
    await metrics.upsert(organization_id=organization_id, campaign_id=None, metric_name="ai_tokens_total", metric_date=day_start, period=_PERIOD, value=total_tokens)

    # Campaign funnel (snapshot, per campaign).
    campaigns, _ = await CampaignRepository(session).list_for_organization(organization_id, page_size=10_000)
    if campaigns:
        funnel_by_campaign = await CampaignLeadRepository(session).funnel_counts_for_campaigns([c.id for c in campaigns])
        for campaign in campaigns:
            counts = funnel_by_campaign.get(campaign.id, {})
            for status in _campaign_lead_statuses():
                await metrics.upsert(
                    organization_id=organization_id, campaign_id=campaign.id, metric_name=f"campaign_funnel__{status}",
                    metric_date=day_start, period=_PERIOD, value=counts.get(status, 0), dimensions={"status": status},
                )

    # Meetings (snapshot).
    meeting_counts = await MeetingRepository(session).status_distribution(organization_id)
    for status in _meeting_statuses():
        await metrics.upsert(
            organization_id=organization_id, campaign_id=None, metric_name=f"meetings__{status}",
            metric_date=day_start, period=_PERIOD, value=meeting_counts.get(status, 0), dimensions={"status": status},
        )


def _campaign_lead_statuses() -> list[str]:
    from app.models.enums import CampaignLeadStatusEnum

    return [s.value for s in CampaignLeadStatusEnum]


def _meeting_statuses() -> list[str]:
    from app.models.enums import MeetingStatusEnum

    return [s.value for s in MeetingStatusEnum]


async def _run_nightly_aggregation(session: AsyncSession) -> None:
    from app.models.identity.models import Organization

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    org_ids = await session.scalars(select(Organization.id).where(Organization.is_active.is_(True)))
    for organization_id in org_ids:
        await _aggregate_for_organization(session, organization_id, now=now, day_start=day_start)
    await session.commit()


@celery_app.task(name="analytics.aggregate_daily_metrics", acks_late=True)
def aggregate_daily_metrics_task() -> None:
    asyncio.run(run_with_fresh_session(_run_nightly_aggregation))


# ─── Scheduled report delivery ───────────────────────────────────────────────────


def _is_due(report, now: datetime) -> bool:
    if not report.is_scheduled or not report.schedule_cron:
        return False
    if report.last_run_at is None:
        return True
    buffer = _DUE_BUFFER.get(report.schedule_cron)
    if buffer is None:
        return False
    return now - report.last_run_at >= buffer


async def _run_due_reports(session: AsyncSession) -> None:
    from app.repositories.report_repository import ReportRepository
    from app.services.analytics.report_service import ReportService
    from app.services.system_actor import resolve_org_owner

    now = datetime.now(timezone.utc)
    due_reports = [r for r in await ReportRepository(session).list_due_scheduled() if _is_due(r, now)]
    for report in due_reports:
        actor = await resolve_org_owner(session, report.organization_id)
        await ReportService(session).run(report, actor=actor)


@celery_app.task(name="analytics.check_scheduled_reports", acks_late=True)
def check_scheduled_reports_task() -> None:
    asyncio.run(run_with_fresh_session(_run_due_reports))
