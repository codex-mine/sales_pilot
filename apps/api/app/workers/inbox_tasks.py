"""
Celery task for the Inbox module's async reply-classification finalize step
(the `inbox` queue). Mirrors `app/workers/email_tasks.py`'s
`finalize_email_generation` exactly: `AIJobService.run_job` already
dispatched the classification job to the `ai` queue; this task polls it to
terminal and then hands off to `InboundEmailService.finalize_classification`
for the parse-and-apply-side-effects step.
"""

import asyncio
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIJob
from app.models.enums import AIJobStatusEnum
from app.repositories.ai_job_repository import AIJobRepository
from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}


async def _wait_for_terminal(session: AsyncSession, job_id: uuid.UUID, organization_id: uuid.UUID) -> AIJob | None:
    settings = get_settings()
    timeout_seconds = settings.ai_job_timeout_seconds * (settings.ai_max_retries + 1) + 60
    jobs = AIJobRepository(session)
    deadline = time.monotonic() + timeout_seconds
    while True:
        job = await jobs.get_by_id(job_id, organization_id)
        if job is None or job.status in _TERMINAL_STATUSES:
            return job
        if time.monotonic() > deadline:
            return job
        await asyncio.sleep(2)


@celery_app.task(name="inbox.finalize_reply_classification", acks_late=True)
def finalize_reply_classification(job_id: str, organization_id: str, message_id: str) -> None:
    from app.services.communication.inbound_email_service import InboundEmailService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        job = await _wait_for_terminal(session, uuid.UUID(job_id), org_uuid)
        if job is None:
            return
        await InboundEmailService(session).finalize_classification(job, uuid.UUID(message_id), org_uuid)

    asyncio.run(run_with_fresh_session(_run))
