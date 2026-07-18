"""
Celery tasks for asynchronous Company Research / Prospect Analysis
orchestration (the `research` queue).

None of these tasks call an LLM SDK or `AIJobService.execute_job` directly —
they poll AIJob rows that were already dispatched to the `ai` queue via
`AIJobService.run_job` (so retry semantics stay owned by `app/workers/ai_tasks.py`)
until the job reaches a terminal status, then hand off to the feature
service's `finalize()`/`trigger_analysis()` for the structured-output ->
CompanyResearch/ProspectAnalysis write. Kept off the `ai` queue so a chain of
waits here never blocks LLM job execution.

None of this runs in eager/test mode: `AIJobService.run_job` executes
synchronously there, so a job is always already terminal by the time a
research-service `trigger_*` method would consider dispatching one of these
tasks (see `CompanyResearchService.trigger_research` /
`ProspectAnalysisService.trigger_analysis`) — the one exception is bulk
research's per-lead fan-out, which branches on `ai_execute_jobs_eagerly`
itself (see `ProspectAnalysisService.bulk_trigger_research`).
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


@celery_app.task(name="research.finalize_company_research", acks_late=True)
def finalize_company_research(job_id: str, organization_id: str, company_id: str, actor_id: str) -> None:
    from app.services.ai.company_research_service import CompanyResearchService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        job = await _wait_for_terminal(session, uuid.UUID(job_id), org_uuid)
        if job is None:
            return
        service = CompanyResearchService(session)
        company = await service.companies.get_by_id(uuid.UUID(company_id), org_uuid)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        if company is None or actor is None:
            return
        await service.finalize(job, company, actor)

    asyncio.run(run_with_fresh_session(_run))


@celery_app.task(name="research.finalize_prospect_analysis", acks_late=True)
def finalize_prospect_analysis(job_id: str, organization_id: str, lead_id: str, actor_id: str) -> None:
    from app.services.ai.prospect_analysis_service import ProspectAnalysisService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        job = await _wait_for_terminal(session, uuid.UUID(job_id), org_uuid)
        if job is None:
            return
        service = ProspectAnalysisService(session)
        lead = await service.leads.get_by_id(uuid.UUID(lead_id), org_uuid)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        if lead is None or actor is None:
            return
        await service.finalize(job, lead, actor)

    asyncio.run(run_with_fresh_session(_run))


@celery_app.task(name="research.orchestrate_lead_research", acks_late=True)
def orchestrate_lead_research(company_job_id: str, organization_id: str, lead_id: str, actor_id: str) -> None:
    """Waits for the company-research job (dispatched by
    `trigger_lead_research` with `auto_finalize=False`) to finish, finalizes
    it, then triggers prospect analysis as the child job — the
    orchestrator -> sub-agent chain `AIJob.parent_job_id` exists for."""
    from app.services.ai.prospect_analysis_service import ProspectAnalysisService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        job = await _wait_for_terminal(session, uuid.UUID(company_job_id), org_uuid)
        service = ProspectAnalysisService(session)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        lead = await service.leads.get_by_id(uuid.UUID(lead_id), org_uuid)
        if actor is None or lead is None:
            return
        if job is not None and lead.company_id:
            company = await service.companies.get_by_id(lead.company_id, org_uuid)
            if company is not None:
                await service.research_service.finalize(job, company, actor)
        await service.trigger_analysis(
            org_uuid, lead.id, actor=actor, parent_job_id=job.id if job is not None else None
        )

    asyncio.run(run_with_fresh_session(_run))


@celery_app.task(name="research.dispatch_lead_research", acks_late=True)
def dispatch_lead_research(lead_id: str, organization_id: str, actor_id: str, force: bool) -> None:
    """Bulk-research fan-out target: runs the full `trigger_lead_research`
    flow (company research + prospect analysis) for one lead, off the
    request thread."""
    from app.services.ai.prospect_analysis_service import ProspectAnalysisService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        service = ProspectAnalysisService(session)
        actor = await UserRepository(session).get_by_id(uuid.UUID(actor_id))
        if actor is None:
            return
        await service.trigger_lead_research(org_uuid, uuid.UUID(lead_id), actor=actor, force=force)

    asyncio.run(run_with_fresh_session(_run))
