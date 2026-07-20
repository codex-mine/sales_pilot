"""
`Metric` rows are the pre-aggregated read layer the module 12 dashboard reads
from instead of scanning `AIJob`/`CampaignLead`/`Meeting` live (see
ARCHITECTURE.md §7's two-tier Event/Metric design). `Metric`'s unique
constraint is exactly `(organization_id, campaign_id, metric_name,
metric_date, period)` — notably NOT including `dimensions`. That means a
sub-breakdown (e.g. AI cost per job_type, campaign funnel per status) can't be
represented as multiple rows sharing one `metric_name` with different
`dimensions` values, since they'd collide on upsert. This module's convention,
followed consistently by `app/workers/analytics_tasks.py`: fold the breakdown
key into `metric_name` itself (e.g. `"ai_cost__research"`,
`"campaign_funnel__replied"`) while still populating `dimensions` for
readability/display. `campaign_id` remains the correct place to scope a metric
to one campaign (it's already part of the uniqueness), as module 08's
email-metrics task does.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remaining_domains import Metric


class MetricRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self, *, organization_id: uuid.UUID, campaign_id: uuid.UUID | None, metric_name: str,
        metric_date: datetime, period: str, value: float, dimensions: dict | None = None,
    ) -> Metric:
        """Select-then-insert-or-update on the exact unique-constraint columns
        — the same idempotency pattern `email_metrics_tasks.py` uses, so
        re-running the nightly job for a day already aggregated updates rows
        in place rather than duplicating them."""
        existing = await self.db.scalar(
            select(Metric).where(
                Metric.organization_id == organization_id,
                Metric.campaign_id == campaign_id,
                Metric.metric_name == metric_name,
                Metric.metric_date == metric_date,
                Metric.period == period,
            )
        )
        if existing is not None:
            existing.value = value
            existing.dimensions = dimensions
            await self.db.flush()
            return existing
        metric = Metric(
            organization_id=organization_id, campaign_id=campaign_id, metric_name=metric_name,
            metric_date=metric_date, period=period, value=value, dimensions=dimensions,
        )
        self.db.add(metric)
        await self.db.flush()
        return metric

    async def get_latest_many(
        self, organization_id: uuid.UUID, metric_names: list[str], *, period: str = "daily"
    ) -> dict[str, Metric]:
        """One query for every named metric the dashboard summary needs
        (org-wide rows only, `campaign_id IS NULL`) — avoids N+1 across
        widgets. Rows are ordered newest-first so the first occurrence per
        `metric_name` in Python is the latest one."""
        if not metric_names:
            return {}
        result = await self.db.scalars(
            select(Metric)
            .where(
                Metric.organization_id == organization_id,
                Metric.campaign_id.is_(None),
                Metric.metric_name.in_(metric_names),
                Metric.period == period,
            )
            .order_by(Metric.metric_date.desc())
        )
        latest: dict[str, Metric] = {}
        for metric in result:
            latest.setdefault(metric.metric_name, metric)
        return latest

    async def get_latest_by_prefix(
        self, organization_id: uuid.UUID, name_prefix: str, *, campaign_id: uuid.UUID | None = None,
        period: str = "daily",
    ) -> list[Metric]:
        """Every metric whose name starts with `name_prefix` (e.g.
        `"campaign_funnel__"`), restricted to the most recent `metric_date`
        available — used to read a whole breakdown (all statuses for a
        funnel) in one query. `name_prefix` itself contains underscores
        (e.g. the `__` separator), which SQL `LIKE` treats as a single-char
        wildcard — escaped here so `"ai_cost__"` doesn't also match
        `"ai_cost_total"`."""
        escaped_prefix = name_prefix.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
        conditions = [
            Metric.organization_id == organization_id,
            Metric.metric_name.like(f"{escaped_prefix}%", escape="\\"),
            Metric.period == period,
        ]
        if campaign_id is not None:
            conditions.append(Metric.campaign_id == campaign_id)
        latest_date = await self.db.scalar(select(Metric.metric_date).where(*conditions).order_by(Metric.metric_date.desc()).limit(1))
        if latest_date is None:
            return []
        result = await self.db.scalars(select(Metric).where(*conditions, Metric.metric_date == latest_date))
        return list(result)

    async def get_series(
        self, organization_id: uuid.UUID, metric_name: str, *, campaign_id: uuid.UUID | None = None,
        period: str = "daily", limit: int = 30,
    ) -> list[Metric]:
        """Most recent `limit` points for one named metric — a trend line."""
        result = await self.db.scalars(
            select(Metric)
            .where(
                Metric.organization_id == organization_id,
                Metric.campaign_id == campaign_id,
                Metric.metric_name == metric_name,
                Metric.period == period,
            )
            .order_by(Metric.metric_date.desc())
            .limit(limit)
        )
        return list(result)[::-1]
