"""
Analytics -> the org-wide dashboard's single composition point.

Query-source decisions (documented per ARCHITECTURE.md §7's "Metric-first"
rule, since a few widgets deliberately deviate from it):

- **Pipeline funnel** and **meeting status breakdown** read `Lead`/`Meeting`
  live (`status_distribution` on each repository) rather than from `Metric`.
  Both tables are small and already indexed on the grouped column, so a live
  GROUP BY is the "cheap even unaggregated" exception the architecture doc
  itself calls out — and it means the two most-checked, lowest-latency-
  tolerance widgets never lag a nightly batch by up to 24h.
- **AI usage**, **campaign performance**, and **email open/click/bounce
  rate** read exclusively from `Metric` — `AIJob`/`CampaignLead` volume grows
  with usage and a live GROUP BY across either at dashboard-load time doesn't
  scale the way a two-row Lead/Meeting status count does. Email rates
  specifically reuse the `Metric` rows module 08's hourly task already
  writes, per the module 12 spec, rather than re-deriving them from
  `EmailEvent`.
- **Recent activity** reads `Activity` live, LIMIT-bounded (not a scan) —
  same "small indexed read" class as Lead/Meeting.
- **Unread notification count** is inherently real-time and explicitly
  exempted by the spec.

`get_dashboard_summary` composes all of the above into one response with a
small, fixed number of queries (not one that grows with org data size), so
the frontend never has to fan out 6+ requests to render the page.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LeadStatusEnum
from app.repositories.activity_repository import ActivityRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.metric_repository import MetricRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.analytics import (
    AIDailyCostPoint,
    AIUsageAnalyticsResponse,
    AIUsageJobTypeBreakdown,
    CampaignPerformanceItem,
    CampaignPerformanceResponse,
    DashboardSummaryResponse,
    EmailPerformanceSummary,
    MeetingsSummary,
    PipelineFunnelResponse,
    RecentActivityItem,
    UpcomingMeetingItem,
)

_EMAIL_METRIC_PERIOD = "hourly"  # matches app/workers/email_metrics_tasks.py
_DAILY_PERIOD = "daily"  # matches app/workers/analytics_tasks.py

logger = structlog.get_logger(__name__)
_T = TypeVar("_T")


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.meetings = MeetingRepository(db)
        self.campaigns = CampaignRepository(db)
        self.activities = ActivityRepository(db)
        self.notifications = NotificationRepository(db)
        self.metrics = MetricRepository(db)

    # ─── Pipeline funnel ────────────────────────────────────────────────────────

    async def get_pipeline_funnel(self, organization_id: uuid.UUID) -> PipelineFunnelResponse:
        counts = await self.leads.status_distribution(organization_id)
        full = {status.value: counts.get(status.value, 0) for status in LeadStatusEnum}
        return PipelineFunnelResponse(counts=full)

    # ─── AI usage ───────────────────────────────────────────────────────────────

    async def get_ai_usage(self, organization_id: uuid.UUID) -> AIUsageAnalyticsResponse:
        totals = await self.metrics.get_latest_many(
            organization_id, ["ai_cost_total", "ai_job_count_total", "ai_tokens_total"], period=_DAILY_PERIOD
        )
        cost_rows = await self.metrics.get_latest_by_prefix(organization_id, "ai_cost__", period=_DAILY_PERIOD)
        count_rows = await self.metrics.get_latest_by_prefix(organization_id, "ai_job_count__", period=_DAILY_PERIOD)
        token_rows = await self.metrics.get_latest_by_prefix(organization_id, "ai_tokens__", period=_DAILY_PERIOD)

        counts_by_type = {m.metric_name.removeprefix("ai_job_count__"): m.value for m in count_rows}
        tokens_by_type = {m.metric_name.removeprefix("ai_tokens__"): m.value for m in token_rows}
        by_job_type = [
            AIUsageJobTypeBreakdown(
                job_type=m.metric_name.removeprefix("ai_cost__"),
                job_count=int(counts_by_type.get(m.metric_name.removeprefix("ai_cost__"), 0)),
                total_tokens=int(tokens_by_type.get(m.metric_name.removeprefix("ai_cost__"), 0)),
                cost_usd=round(m.value, 6),
            )
            for m in cost_rows
        ]
        by_job_type.sort(key=lambda item: item.cost_usd, reverse=True)

        trend_rows = await self.metrics.get_series(organization_id, "ai_cost_total", period=_DAILY_PERIOD, limit=30)
        daily_cost_trend = [AIDailyCostPoint(date=m.metric_date.date().isoformat(), cost_usd=round(m.value, 6)) for m in trend_rows]

        return AIUsageAnalyticsResponse(
            total_cost_usd=round(totals["ai_cost_total"].value, 6) if "ai_cost_total" in totals else 0.0,
            total_job_count=int(totals["ai_job_count_total"].value) if "ai_job_count_total" in totals else 0,
            total_tokens=int(totals["ai_tokens_total"].value) if "ai_tokens_total" in totals else 0,
            by_job_type=by_job_type,
            daily_cost_trend=daily_cost_trend,
        )

    # ─── Campaign performance ──────────────────────────────────────────────────

    async def get_campaign_performance(self, organization_id: uuid.UUID, *, limit: int = 10) -> CampaignPerformanceResponse:
        campaigns, _ = await self.campaigns.list_for_organization(organization_id, page_size=200)
        items: list[CampaignPerformanceItem] = []
        for campaign in campaigns:
            rows = await self.metrics.get_latest_by_prefix(
                organization_id, "campaign_funnel__", campaign_id=campaign.id, period=_DAILY_PERIOD
            )
            if not rows:
                continue
            status_counts = {m.metric_name.removeprefix("campaign_funnel__"): int(m.value) for m in rows}
            enrolled_total = sum(status_counts.values())
            replied = status_counts.get("replied", 0)
            meeting_booked = status_counts.get("meeting_booked", 0)
            reply_rate = round(replied / enrolled_total * 100, 1) if enrolled_total else 0.0
            items.append(
                CampaignPerformanceItem(
                    campaign_id=str(campaign.id), campaign_name=campaign.name, status=campaign.status,
                    enrolled_count=enrolled_total, replied_count=replied, meeting_booked_count=meeting_booked,
                    reply_rate=reply_rate,
                )
            )
        items.sort(key=lambda item: item.reply_rate, reverse=True)
        return CampaignPerformanceResponse(campaigns=items[:limit])

    # ─── Email performance ──────────────────────────────────────────────────────

    async def get_email_performance(self, organization_id: uuid.UUID) -> EmailPerformanceSummary:
        rates = await self.metrics.get_latest_many(
            organization_id, ["email_open_rate", "email_click_rate", "email_bounce_rate"], period=_EMAIL_METRIC_PERIOD
        )

        def _pct(name: str) -> float:
            return round(rates[name].value * 100, 1) if name in rates else 0.0

        return EmailPerformanceSummary(
            open_rate=_pct("email_open_rate"), click_rate=_pct("email_click_rate"), bounce_rate=_pct("email_bounce_rate"),
        )

    # ─── Meetings ───────────────────────────────────────────────────────────────

    async def get_meetings_summary(self, organization_id: uuid.UUID) -> MeetingsSummary:
        by_status = await self.meetings.status_distribution(organization_id)
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        upcoming_meetings, _ = await self.meetings.list_for_org(
            organization_id, status=["proposed", "confirmed"], date_from=now, date_to=now + timedelta(days=7),
            page=1, page_size=10,
        )
        # "Booked this month" = meetings whose slot falls within the current
        # calendar month — reuses the existing scheduled_start filter rather
        # than adding a created_at filter for a single dashboard number.
        _, booked_this_month = await self.meetings.list_for_org(
            organization_id, date_from=month_start, page=1, page_size=1
        )

        return MeetingsSummary(
            by_status=by_status,
            booked_this_month=booked_this_month,
            upcoming=[
                UpcomingMeetingItem(
                    id=str(m.id), title=m.title,
                    lead_full_name=m.lead.full_name if m.lead else None,
                    scheduled_start=m.scheduled_start,
                )
                for m in upcoming_meetings
            ],
        )

    # ─── Recent activity ────────────────────────────────────────────────────────

    async def get_recent_activity(self, organization_id: uuid.UUID, *, limit: int = 15) -> list[RecentActivityItem]:
        activities, _ = await self.activities.list_for_organization(organization_id, page=1, page_size=limit)
        return [
            RecentActivityItem(
                id=str(a.id), activity_type=a.activity_type, summary=a.summary,
                actor_name=a.actor.full_name if a.actor else None, occurred_at=a.occurred_at,
            )
            for a in activities
        ]

    # ─── Composed summary ───────────────────────────────────────────────────────

    async def _safe(self, widget_name: str, factory: Callable[[], Awaitable[_T]], default: _T) -> _T:
        """Runs one widget's query inside a SAVEPOINT so a failure there
        can't poison the outer request-scoped transaction for the rest of
        the summary, and swallows the exception (logged) in favor of a safe
        default — one broken data source must never 500 the whole
        dashboard. `get_dashboard_summary`'s own test mocks a widget's data
        source failing and asserts every other section still comes back."""
        try:
            async with self.db.begin_nested():
                return await factory()
        except Exception as exc:  # noqa: BLE001 — intentionally broad: any widget failure must not break the page
            logger.error("dashboard_widget_failed", widget=widget_name, error=str(exc))
            return default

    async def get_dashboard_summary(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            pipeline_funnel=await self._safe(
                "pipeline_funnel", lambda: self.get_pipeline_funnel(organization_id), PipelineFunnelResponse(counts={})
            ),
            ai_usage=await self._safe(
                "ai_usage", lambda: self.get_ai_usage(organization_id),
                AIUsageAnalyticsResponse(total_cost_usd=0.0, total_job_count=0, total_tokens=0, by_job_type=[], daily_cost_trend=[]),
            ),
            campaign_performance=await self._safe(
                "campaign_performance", lambda: self.get_campaign_performance(organization_id),
                CampaignPerformanceResponse(campaigns=[]),
            ),
            email_performance=await self._safe(
                "email_performance", lambda: self.get_email_performance(organization_id),
                EmailPerformanceSummary(open_rate=0.0, click_rate=0.0, bounce_rate=0.0),
            ),
            meetings=await self._safe(
                "meetings", lambda: self.get_meetings_summary(organization_id),
                MeetingsSummary(by_status={}, booked_this_month=0, upcoming=[]),
            ),
            recent_activity=await self._safe("recent_activity", lambda: self.get_recent_activity(organization_id), []),
            unread_notification_count=await self._safe(
                "unread_notifications", lambda: self.notifications.unread_count(organization_id, user_id), 0
            ),
        )
