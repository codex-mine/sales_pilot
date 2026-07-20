import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai.models import AIJob
from app.models.enums import AIJobStatusEnum


class AIJobRepository:
    """AIJob rows are append-mostly: inserts plus status/completion-field
    transitions only. Nothing here ever deletes a job or rewrites its
    input_data — that immutability is what makes the table an audit log."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> AIJob | None:
        return await self.db.scalar(
            select(AIJob)
            .options(selectinload(AIJob.outputs), selectinload(AIJob.agent))
            .execution_options(populate_existing=True)
            .where(AIJob.id == job_id, AIJob.organization_id == organization_id)
        )

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        job_type: str,
        agent_id: uuid.UUID | None,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        initiated_by: uuid.UUID | None,
        parent_job_id: uuid.UUID | None,
        provider: str | None,
        model_name: str | None,
        prompt_version_id: uuid.UUID | None,
        input_data: dict | None,
        max_retries: int,
    ) -> AIJob:
        job = AIJob(
            organization_id=organization_id,
            job_type=job_type,
            agent_id=agent_id,
            entity_type=entity_type,
            entity_id=entity_id,
            initiated_by=initiated_by,
            parent_job_id=parent_job_id,
            provider=provider,
            model_name=model_name,
            prompt_version_id=prompt_version_id,
            input_data=input_data,
            max_retries=max_retries,
            status=AIJobStatusEnum.PENDING,
            created_by=initiated_by,
            updated_by=initiated_by,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def mark_running(self, job: AIJob) -> AIJob:
        job.status = AIJobStatusEnum.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    async def mark_completed(
        self, job: AIJob, *, input_tokens: int, output_tokens: int, cost_usd: float, latency_ms: int
    ) -> AIJob:
        job.status = AIJobStatusEnum.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.input_tokens = input_tokens
        job.output_tokens = output_tokens
        job.total_tokens = input_tokens + output_tokens
        job.cost_usd = cost_usd
        job.latency_ms = latency_ms
        await self.db.flush()
        return job

    async def mark_failed(self, job: AIJob, *, error_message: str, error_traceback: str | None = None) -> AIJob:
        job.status = AIJobStatusEnum.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        job.error_traceback = error_traceback
        await self.db.flush()
        return job

    async def mark_retrying(self, job: AIJob) -> AIJob:
        job.status = AIJobStatusEnum.RETRYING
        job.retry_count += 1
        await self.db.flush()
        return job

    async def mark_cancelled(self, job: AIJob) -> AIJob:
        job.status = AIJobStatusEnum.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    # ─── List / filter / paginate ─────────────────────────────────────────────

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None = None,
        job_type: list[str] | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[AIJob], int]:
        conditions: list[Any] = [AIJob.organization_id == organization_id]
        if status:
            conditions.append(AIJob.status.in_(status))
        if job_type:
            conditions.append(AIJob.job_type.in_(job_type))
        if entity_type:
            conditions.append(AIJob.entity_type == entity_type)
        if entity_id:
            conditions.append(AIJob.entity_id == entity_id)
        if created_from:
            conditions.append(AIJob.created_at >= created_from)
        if created_to:
            conditions.append(AIJob.created_at <= created_to)

        total = await self.db.scalar(select(func.count(AIJob.id)).where(*conditions)) or 0
        rows = await self.db.scalars(
            select(AIJob)
            .options(selectinload(AIJob.outputs), selectinload(AIJob.agent))
            .where(*conditions)
            .order_by(AIJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), total

    # ─── Usage aggregation ────────────────────────────────────────────────────

    async def usage_summary(
        self, organization_id: uuid.UUID, *, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Spend/token/job-count rollup grouped by job_type — feeds the cost
        dashboard without shipping raw job rows to the client."""
        conditions: list[Any] = [AIJob.organization_id == organization_id]
        if since:
            conditions.append(AIJob.created_at >= since)
        rows = await self.db.execute(
            select(
                AIJob.job_type,
                func.count(AIJob.id),
                func.coalesce(func.sum(AIJob.total_tokens), 0),
                func.coalesce(func.sum(AIJob.cost_usd), 0.0),
                func.coalesce(func.avg(AIJob.latency_ms), 0.0),
            )
            .where(*conditions)
            .group_by(AIJob.job_type)
            .order_by(func.sum(AIJob.cost_usd).desc())
        )
        return [
            {
                "job_type": job_type,
                "job_count": count,
                "total_tokens": int(tokens),
                "cost_usd": round(float(cost), 6),
                "avg_latency_ms": int(latency),
            }
            for job_type, count, tokens, cost, latency in rows.all()
        ]

    async def usage_summary_for_window(self, organization_id: uuid.UUID, *, start: datetime) -> list[dict[str, Any]]:
        """Same rollup as `usage_summary` — an open-ended `created_at >= start`
        filter, deliberately with NO upper bound. An exclusive upper bound
        compared against the *application* server's clock is fragile against
        ordinary app/DB clock skew (a `server_default=func.now()` timestamp
        can legitimately land a few seconds "ahead" of `datetime.now()` in the
        calling process), and module 12's nightly task only needs "the
        trailing 24h as of now," not a precisely bounded window — the daily
        upsert already makes re-running idempotent regardless."""
        rows = await self.db.execute(
            select(
                AIJob.job_type,
                func.count(AIJob.id),
                func.coalesce(func.sum(AIJob.total_tokens), 0),
                func.coalesce(func.sum(AIJob.cost_usd), 0.0),
            )
            .where(AIJob.organization_id == organization_id, AIJob.created_at >= start)
            .group_by(AIJob.job_type)
        )
        return [
            {"job_type": job_type, "job_count": count, "total_tokens": int(tokens), "cost_usd": round(float(cost), 6)}
            for job_type, count, tokens, cost in rows.all()
        ]

    async def daily_costs(
        self, organization_id: uuid.UUID, *, since: datetime
    ) -> list[dict[str, Any]]:
        day = func.date_trunc("day", AIJob.created_at)
        rows = await self.db.execute(
            select(day, func.coalesce(func.sum(AIJob.cost_usd), 0.0))
            .where(AIJob.organization_id == organization_id, AIJob.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
        return [{"date": d.date().isoformat(), "cost_usd": round(float(c), 6)} for d, c in rows.all()]
