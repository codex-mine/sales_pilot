"""
AI -> Prospect Analysis, and the combined "Research this Lead" orchestration.

Mirrors CompanyResearchService's trigger/finalize shape for a single lead
(`trigger_analysis` / `finalize`), and additionally implements
`trigger_lead_research`: the orchestrator -> sub-agent chain that runs
company research (parent job, if stale/missing) then prospect analysis
(child job, `parent_job_id` set) for a lead, exactly the pattern
`AIJob.parent_job_id` exists for.

Lead.status transitions (RESEARCHING -> RESEARCH_DONE) always go through
`LeadService.update()` so its own Activity/AuditLog side effects fire —
nothing here writes to the Lead row directly.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import AIJob
from app.models.crm.models import Lead
from app.models.enums import AIAgentTypeEnum, AIJobStatusEnum, AuditActionEnum, LeadStatusEnum
from app.models.identity.models import User
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_research_repository import CompanyResearchRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.prospect_analysis_repository import ProspectAnalysisRepository
from app.schemas.leads import LeadUpdateRequest
from app.services.ai.ai_job_service import AIJobService
from app.services.ai.company_research_service import CompanyResearchService
from app.services.lead_service import LeadService

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}


class ProspectAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.companies = CompanyRepository(db)
        self.analyses = ProspectAnalysisRepository(db)
        self.research_repo = CompanyResearchRepository(db)
        self.ai_jobs = AIJobRepository(db)
        self.ai_job_service = AIJobService(db)
        self.audit_log = AuditLogRepository(db)
        self.lead_service = LeadService(db)
        self.research_service = CompanyResearchService(db)

    async def require_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> Lead:
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        return lead

    # ─── Single-lead prospect analysis ───────────────────────────────────────────

    async def trigger_analysis(
        self,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
        *,
        actor: User,
        parent_job_id: uuid.UUID | None = None,
    ) -> AIJob:
        lead = await self.require_lead(lead_id, organization_id)
        company_research = None
        if lead.company_id:
            company_research = await self.research_repo.get_by_company(lead.company_id, organization_id)

        job = await self.ai_job_service.run_job(
            organization_id=organization_id,
            job_type="analyze_prospect",
            entity_type="lead",
            entity_id=lead.id,
            prompt_template_name="analyze_prospect",
            variables={
                "lead_first_name": lead.first_name or "",
                "lead_job_title": lead.job_title or "",
                "lead_company_name": lead.company_name or "",
                "company_research_summary": (
                    company_research.summary if company_research and company_research.summary
                    else "No company research available yet."
                ),
            },
            agent_type=AIAgentTypeEnum.PROSPECT_ANALYSIS,
            initiated_by=actor.id,
            parent_job_id=parent_job_id,
            response_format="json",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="prospect_analysis", resource_id=lead.id,
            changes={"event": "prospect_analysis_triggered", "ai_job_id": str(job.id)},
        )
        await self.db.commit()

        if job.status in _TERMINAL_STATUSES:
            job = await self.finalize(job, lead, actor)
        else:
            from app.workers.research_tasks import finalize_prospect_analysis

            finalize_prospect_analysis.apply_async(
                args=[str(job.id), str(organization_id), str(lead.id), str(actor.id)],
                queue="research",
            )
        return job

    async def finalize(self, job: AIJob, lead: Lead, actor: User) -> AIJob:
        if job.status != AIJobStatusEnum.COMPLETED:
            await self.audit_log.record(
                organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="prospect_analysis", resource_id=lead.id,
                changes={
                    "event": "prospect_analysis_failed",
                    "ai_job_id": str(job.id),
                    "error": job.error_message,
                },
            )
        else:
            output = job.outputs[-1] if job.outputs else None
            parsed: dict[str, Any] = dict(output.content_json) if output and output.content_json else {}
            await self.analyses.upsert(
                lead_id=lead.id,
                organization_id=lead.organization_id,
                ai_job_id=job.id,
                buying_intent=parsed.get("buying_intent"),
                priority_score=parsed.get("priority_score"),
                recommended_approach=parsed.get("recommended_approach"),
                value_proposition=parsed.get("value_proposition"),
                predicted_objections=parsed.get("predicted_objections"),
                likely_goals=parsed.get("likely_goals"),
                decision_authority=parsed.get("decision_authority"),
                best_contact_time=parsed.get("best_contact_time"),
                full_analysis=parsed,
            )
            await self.audit_log.record(
                organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="prospect_analysis", resource_id=lead.id,
                changes={"event": "prospect_analysis_completed", "ai_job_id": str(job.id)},
            )
        await self._sync_lead_status(lead, actor)
        await self.db.commit()
        return job

    async def _sync_lead_status(self, lead: Lead, actor: User) -> None:
        """Flips RESEARCHING -> RESEARCH_DONE once this lead's prospect
        analysis has reached a terminal state. Goes through LeadService.update
        so the usual STATUS_CHANGED Activity/AuditLog side effects fire."""
        fresh = await self.leads.get_by_id(lead.id, lead.organization_id)
        if fresh is not None and fresh.status == LeadStatusEnum.RESEARCHING.value:
            await self.lead_service.update(
                fresh, payload=LeadUpdateRequest(status=LeadStatusEnum.RESEARCH_DONE.value), actor=actor
            )

    # ─── Combined "Research this Lead" orchestration ─────────────────────────────

    async def trigger_lead_research(
        self, organization_id: uuid.UUID, lead_id: uuid.UUID, *, actor: User, force: bool = False
    ) -> tuple[AIJob | None, AIJob | None]:
        """Returns (company_job, prospect_job). `prospect_job` is None when
        company research is still in flight (async/production mode) — a
        `research`-queue task takes over and creates it once company
        research finishes; poll `get_lead_research_status` for the result."""
        lead = await self.require_lead(lead_id, organization_id)
        await self.lead_service.update(
            lead, payload=LeadUpdateRequest(status=LeadStatusEnum.RESEARCHING.value), actor=actor
        )
        lead = await self.require_lead(lead_id, organization_id)

        company_job: AIJob | None = None
        if lead.company_id:
            company_job = await self.research_service.trigger_research(
                organization_id, lead.company_id, actor=actor, force=force, auto_finalize=False,
            )

        if company_job is None or company_job.status in _TERMINAL_STATUSES:
            prospect_job = await self.trigger_analysis(
                organization_id, lead.id, actor=actor,
                parent_job_id=company_job.id if company_job else None,
            )
            return company_job, prospect_job

        from app.workers.research_tasks import orchestrate_lead_research

        orchestrate_lead_research.apply_async(
            args=[str(company_job.id), str(organization_id), str(lead_id), str(actor.id)],
            queue="research",
        )
        return company_job, None

    async def get_lead_research_status(
        self, organization_id: uuid.UUID, lead: Lead
    ) -> tuple[AIJob | None, AIJob | None]:
        company_job = None
        if lead.company_id:
            jobs, _total = await self.ai_jobs.list_for_organization(
                organization_id, job_type=["research_company"], entity_type="company",
                entity_id=lead.company_id, page=1, page_size=1,
            )
            company_job = jobs[0] if jobs else None
        jobs, _total = await self.ai_jobs.list_for_organization(
            organization_id, job_type=["analyze_prospect"], entity_type="lead",
            entity_id=lead.id, page=1, page_size=1,
        )
        prospect_job = jobs[0] if jobs else None
        return company_job, prospect_job

    # ─── Bulk ─────────────────────────────────────────────────────────────────────

    async def bulk_trigger_research(
        self, organization_id: uuid.UUID, lead_ids: list[str], *, actor: User
    ) -> tuple[int, list[str]]:
        parsed_ids: list[uuid.UUID] = []
        errors: list[str] = []
        for raw_id in lead_ids:
            try:
                parsed_ids.append(uuid.UUID(raw_id))
            except ValueError:
                errors.append(f"{raw_id}: not a valid lead id.")

        leads = await self.leads.get_many_by_ids(parsed_ids, organization_id) if parsed_ids else []
        found_ids = {lead.id for lead in leads}
        errors.extend(f"{lid}: lead not found in this organization." for lid in parsed_ids if lid not in found_ids)

        eager = get_settings().ai_execute_jobs_eagerly
        queued = 0
        for lead in leads:
            try:
                if eager:
                    # Mirrors AIJobService.run_job's own eager/async branch —
                    # in eager (dev/test) mode there is no worker to pick up
                    # a dispatched task, so run the whole flow inline instead.
                    await self.trigger_lead_research(organization_id, lead.id, actor=actor, force=False)
                else:
                    from app.workers.research_tasks import dispatch_lead_research

                    dispatch_lead_research.apply_async(
                        args=[str(lead.id), str(organization_id), str(actor.id), False],
                        queue="research",
                    )
                queued += 1
            except (ValidationError, NotFoundError) as exc:
                errors.append(f"{lead.id}: {exc}")

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="lead", resource_id=None,
            changes={"event": "bulk_research_triggered", "requested": len(lead_ids), "queued": queued},
        )
        await self.db.commit()
        return queued, errors
