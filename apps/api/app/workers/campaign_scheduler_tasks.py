"""
Celery beat + worker tasks for Campaigns -> Multi-Step Sequence Automation.

`dispatch_due_campaign_steps` runs every 60 seconds (see `celery_app.py`'s
`beat_schedule`) and is the ONLY place that claims due CampaignLead rows —
`SELECT ... FOR UPDATE SKIP LOCKED` plus immediately clearing
`next_action_at` on the claimed rows, in the same transaction, per `models/
ARCHITECTURE.md` §3. This is what makes concurrent scheduler passes
(overlapping beat ticks, or multiple beat instances) mutually exclusive
without a distributed lock manager: whichever transaction's `SELECT FOR
UPDATE` wins a row, the other's `SKIP LOCKED` silently excludes it — and once
the winner's `next_action_at = NULL` update commits, the row is no longer
"due" for anyone, so a second pass starting right after can't re-claim it
even though the winner hasn't actually processed it yet.

`execute_campaign_step` is the per-row worker task, dispatched once per
claimed CampaignLead — thin by design; all the actual logic lives in
`CampaignSchedulerService`.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.campaign_lead_repository import CampaignLeadRepository
from app.services.campaigns.campaign_scheduler_service import CampaignSchedulerService
from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

_BATCH_SIZE = 200


@celery_app.task(name="campaigns.dispatch_due_steps", acks_late=True)
def dispatch_due_campaign_steps() -> None:
    claimed_ids: list[str] = []

    async def _run(session: AsyncSession) -> None:
        nonlocal claimed_ids
        now = datetime.now(timezone.utc)
        ids = await CampaignLeadRepository(session).claim_due_batch(now=now, batch_size=_BATCH_SIZE)
        await session.commit()  # releases the row locks; claimed rows now have next_action_at = NULL
        claimed_ids = [str(campaign_lead_id) for campaign_lead_id in ids]

    asyncio.run(run_with_fresh_session(_run))

    for campaign_lead_id in claimed_ids:
        execute_campaign_step.apply_async(args=[campaign_lead_id], queue="campaigns")


def _execute_step_time_limit() -> int:
    """An AI-personalized step polls for its generation result inline (see
    `CampaignSchedulerService._wait_for_variant`), so this task's own time
    limit must comfortably exceed that poll's own timeout budget — the
    module-wide `task_soft_time_limit` default (sized for a single LLM call,
    not a poll loop) would kill this task mid-wait otherwise."""
    from app.core.config import get_settings

    settings = get_settings()
    return settings.ai_job_timeout_seconds * (settings.ai_max_retries + 1) + 120


@celery_app.task(
    name="campaigns.execute_step", acks_late=True,
    soft_time_limit=_execute_step_time_limit(), time_limit=_execute_step_time_limit() + 30,
)
def execute_campaign_step(campaign_lead_id: str) -> None:
    async def _run(session: AsyncSession) -> None:
        await CampaignSchedulerService(session).execute_step(uuid.UUID(campaign_lead_id))

    asyncio.run(run_with_fresh_session(_run))
