"""
Celery tasks for asynchronous Email Generation orchestration (the `email`
queue).

Mirrors `app/workers/research_tasks.py` exactly: these tasks never call an
LLM SDK or `AIJobService.execute_job` directly — they poll an AIJob already
dispatched to the `ai` queue via `AIJobService.run_job` until terminal, then
hand off to `EmailGenerationService.finalize()` for the JSON-array ->
per-variant `AIOutput` rows split. None of this runs in eager/test mode
(`run_job` executes inline there, so the job is already terminal by the time
a `generate_email` call would consider dispatching) except bulk generation's
per-lead fan-out, which branches on `ai_execute_jobs_eagerly` itself.
"""

import asyncio
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIJob
from app.models.enums import AIJobStatusEnum
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.user_repository import UserRepository
from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}


async def _wait_for_terminal(
    session: AsyncSession, job_id: uuid.UUID, organization_id: uuid.UUID
) -> AIJob | None:
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


@celery_app.task(name="email.finalize_email_generation", acks_late=True)
def finalize_email_generation(job_id: str, organization_id: str, lead_id: str, actor_id: str) -> None:
    from app.services.ai.email_generation_service import EmailGenerationService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        job = await _wait_for_terminal(session, uuid.UUID(job_id), org_uuid)
        if job is None:
            return
        service = EmailGenerationService(session)
        lead = await service.leads.get_by_id(uuid.UUID(lead_id), org_uuid)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        if lead is None or actor is None:
            return
        await service.finalize(job, lead, actor)

    asyncio.run(run_with_fresh_session(_run))


@celery_app.task(name="email.dispatch_lead_email_generation", acks_late=True)
def dispatch_lead_email_generation(
    lead_id: str, organization_id: str, actor_id: str, template_type: str, tone: str, variant_count: int
) -> None:
    """Bulk-generation fan-out target: runs the full `generate_email` flow
    (including the research auto-trigger, if needed) for one lead, off the
    request thread."""
    from app.models.enums import EmailTemplateTypeEnum, EmailToneEnum
    from app.services.ai.email_generation_service import EmailGenerationService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        service = EmailGenerationService(session)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        if actor is None:
            return
        await service.generate_email(
            org_uuid, uuid.UUID(lead_id), actor=actor,
            template_type=EmailTemplateTypeEnum(template_type), tone=EmailToneEnum(tone),
            variant_count=variant_count,
        )

    asyncio.run(run_with_fresh_session(_run))
