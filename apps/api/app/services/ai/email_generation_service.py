"""
AI -> Personalized Email Generation & Human Review.

`generate_email` never calls an LLM SDK directly — it builds a context blob
from CompanyResearch + ProspectAnalysis + Lead fields, then calls
`AIJobService.run_job(...)` with `response_format="json"`, requesting an
array of `variant_count` `{subject, body_html, body_text, reasoning}`
objects. Finalization (splitting that array into individually-approvable
`AIOutput` rows, `output_type="email_variant"`) happens either inline right
after `run_job` returns (eager/test mode) or via a `email`-queue Celery task
that polls the job to terminal (production/async mode) — the exact same
two-path shape as `CompanyResearchService`/`ProspectAnalysisService`.

Approval (`approve_variant`) is the human gate: it never sends anything —
it just creates a DRAFT `Email` row. Sending is a separate module.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import AIJob, AIOutput, CompanyResearch, ProspectAnalysis
from app.models.campaigns.models import EmailTemplate
from app.models.communication.models import Email
from app.models.crm.models import Lead
from app.models.enums import (
    ActivityTypeEnum,
    AIAgentTypeEnum,
    AIJobStatusEnum,
    AuditActionEnum,
    EmailStatusEnum,
    EmailTemplateTypeEnum,
    EmailToneEnum,
    LeadStatusEnum,
)
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.ai_output_repository import AIOutputRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_research_repository import CompanyResearchRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.email_template_repository import EmailTemplateRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.prospect_analysis_repository import ProspectAnalysisRepository
from app.schemas.leads import LeadUpdateRequest
from app.services.ai.ai_job_service import AIJobService
from app.services.ai.prospect_analysis_service import ProspectAnalysisService
from app.services.lead_service import LeadService

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}
_OUTPUT_TYPE = "email_variant"


class EmailGenerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.companies = CompanyRepository(db)
        self.research_repo = CompanyResearchRepository(db)
        self.analyses = ProspectAnalysisRepository(db)
        self.emails = EmailRepository(db)
        self.templates = EmailTemplateRepository(db)
        self.ai_jobs = AIJobRepository(db)
        self.ai_outputs = AIOutputRepository(db)
        self.ai_job_service = AIJobService(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.lead_service = LeadService(db)
        self.prospect_service = ProspectAnalysisService(db)

    async def require_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> Lead:
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        return lead

    # ─── Generate / regenerate ───────────────────────────────────────────────────

    async def generate_email(
        self,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
        *,
        actor: User,
        template_type: EmailTemplateTypeEnum,
        tone: EmailToneEnum,
        variant_count: int = 2,
        custom_instruction: str | None = None,
        regenerate_from_output_id: uuid.UUID | None = None,
    ) -> AIJob:
        lead = await self.require_lead(lead_id, organization_id)
        analysis = await self.analyses.get_by_lead(lead_id, organization_id)

        if analysis is None:
            # Auto-trigger the combined research flow rather than raising —
            # this matches the pipeline's "research -> write" as one
            # continuous flow instead of forcing a separate manual step, and
            # avoids ever generating a generic email from empty context.
            await self.prospect_service.trigger_lead_research(organization_id, lead_id, actor=actor, force=False)
            analysis = await self.analyses.get_by_lead(lead_id, organization_id)
            if analysis is None:
                # Async/production mode: research was just queued but hasn't
                # finished. Fail clearly instead of generating ungrounded copy.
                raise ValidationError(
                    "This lead needs research before an email can be generated. "
                    "Research has just been triggered — try again once it completes.",
                    errors={"lead_id": ["Research not yet available."]},
                )

        company_research = None
        if lead.company_id:
            company_research = await self.research_repo.get_by_company(lead.company_id, organization_id)

        prior_content: dict[str, Any] | None = None
        if regenerate_from_output_id:
            prior_output = await self.ai_outputs.get_by_id(regenerate_from_output_id, organization_id)
            if prior_output is None or prior_output.output_type != _OUTPUT_TYPE:
                raise NotFoundError("Prior email variant not found.")
            if prior_output.is_approved is not False:
                await self.ai_outputs.set_approval(prior_output, approved=False, approved_by=actor.id)
            if isinstance(prior_output.content_json, dict):
                prior_content = prior_output.content_json

        context = self._build_context(company_research, analysis, custom_instruction, prior_content)

        job = await self.ai_job_service.run_job(
            organization_id=organization_id,
            job_type="generate_email",
            entity_type="lead",
            entity_id=lead.id,
            prompt_template_name="generate_email",
            variables={
                "lead_first_name": lead.first_name or "",
                "lead_job_title": lead.job_title or "",
                "company_name": lead.company_name or "",
                "context": context,
                "tone": tone.value,
                "variant_count": variant_count,
                "template_type": template_type.value,
            },
            agent_type=AIAgentTypeEnum.EMAIL_GENERATION,
            initiated_by=actor.id,
            response_format="json",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="email_generation", resource_id=lead.id,
            changes={
                "event": "email_generation_triggered",
                "ai_job_id": str(job.id),
                "regenerated_from": str(regenerate_from_output_id) if regenerate_from_output_id else None,
            },
        )
        await self.db.commit()

        if job.status in _TERMINAL_STATUSES:
            job = await self.finalize(job, lead, actor)
        else:
            from app.workers.email_tasks import finalize_email_generation

            finalize_email_generation.apply_async(
                args=[str(job.id), str(organization_id), str(lead_id), str(actor.id)], queue="email",
            )
        return job

    def _build_context(
        self,
        company_research: CompanyResearch | None,
        analysis: ProspectAnalysis,
        custom_instruction: str | None,
        prior_content: dict[str, Any] | None,
    ) -> str:
        lines: list[str] = []
        if company_research and company_research.summary:
            lines.append(f"Company summary: {company_research.summary}")
        if company_research and company_research.pain_points:
            lines.append(f"Company pain points: {'; '.join(str(p) for p in company_research.pain_points)}")
        if company_research and company_research.products_services:
            lines.append(
                "Their products/services: " + "; ".join(str(p) for p in company_research.products_services)
            )
        if analysis.buying_intent:
            lines.append(f"Buying intent: {analysis.buying_intent}")
        if analysis.recommended_approach:
            lines.append(f"Recommended approach: {analysis.recommended_approach}")
        if analysis.value_proposition:
            lines.append(f"Value proposition to lead with: {analysis.value_proposition}")
        if analysis.predicted_objections:
            lines.append(
                "Objections to preempt: " + "; ".join(str(o) for o in analysis.predicted_objections)
            )
        if custom_instruction:
            lines.append(f"Additional instruction from the sender: {custom_instruction}")
        if prior_content:
            prior_body = prior_content.get("body_text") or prior_content.get("body_html") or ""
            lines.append(
                "A previous draft was rejected — write a genuinely different email, not a "
                f"light edit. Previous subject: {prior_content.get('subject', '')!r}. Previous "
                f"body (for reference, do not repeat it): {prior_body!r}"
            )
        return "\n".join(lines) if lines else "No additional research context available."

    # ─── Finalize ───────────────────────────────────────────────────────────────

    async def finalize(self, job: AIJob, lead: Lead, actor: User) -> AIJob:
        if job.status != AIJobStatusEnum.COMPLETED:
            await self.audit_log.record(
                organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email_generation", resource_id=lead.id,
                changes={"event": "email_generation_failed", "ai_job_id": str(job.id), "error": job.error_message},
            )
            await self.db.commit()
            return job

        raw_output = job.outputs[-1] if job.outputs else None
        parsed = raw_output.content_json if raw_output else None
        variants: list[dict[str, Any]]
        if isinstance(parsed, list):
            variants = [v for v in parsed if isinstance(v, dict)]
        elif isinstance(parsed, dict):
            variants = [parsed]
        else:
            variants = []

        if not variants:
            await self.audit_log.record(
                organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email_generation", resource_id=lead.id,
                changes={"event": "email_generation_failed", "ai_job_id": str(job.id), "error": "No variants parsed."},
            )
            await self.db.commit()
            return job

        for variant in variants:
            await self.ai_outputs.create(
                job_id=job.id, organization_id=lead.organization_id, output_type=_OUTPUT_TYPE,
                content_text=str(variant.get("subject") or ""), content_json=variant,
            )

        await self.activities.record(
            organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.AI_EMAIL_GENERATED,
            summary=f"{len(variants)} email variant(s) generated for {lead.full_name}",
        )
        await self.audit_log.record(
            organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_generation", resource_id=lead.id,
            changes={"event": "email_generation_completed", "ai_job_id": str(job.id), "variant_count": len(variants)},
        )
        await self.db.commit()
        return job

    # ─── Approve / reject ─────────────────────────────────────────────────────────

    async def approve_variant(
        self,
        organization_id: uuid.UUID,
        output_id: uuid.UUID,
        *,
        actor: User,
        edited_subject: str | None = None,
        edited_body_html: str | None = None,
        edited_body_text: str | None = None,
        save_as_template: bool = False,
        template_name: str | None = None,
        from_email: str,
        from_name: str | None = None,
    ) -> Email:
        output, lead = await self._require_variant_and_lead(output_id, organization_id)
        if not lead.email:
            raise ValidationError(
                "This lead has no email address on file.", errors={"lead_id": ["Missing email."]}
            )

        content: dict[str, Any] = output.content_json if isinstance(output.content_json, dict) else {}
        final_subject = edited_subject if edited_subject is not None else str(content.get("subject") or "")
        final_body_html = edited_body_html if edited_body_html is not None else str(content.get("body_html") or "")
        final_body_text = edited_body_text if edited_body_text is not None else content.get("body_text")
        was_edited = bool(
            (edited_subject is not None and edited_subject != content.get("subject"))
            or (edited_body_html is not None and edited_body_html != content.get("body_html"))
            or (edited_body_text is not None and edited_body_text != content.get("body_text"))
        )

        await self.ai_outputs.set_approval(output, approved=True, approved_by=actor.id)

        template = None
        if save_as_template:
            template = await self._save_as_template(
                organization_id, output, lead, content, actor,
                subject=final_subject, body_html=final_body_html, body_text=final_body_text,
                template_name=template_name,
            )

        email = await self.emails.create(
            organization_id=organization_id, lead_id=lead.id,
            from_email=from_email, from_name=from_name,
            to_email=lead.email, to_name=lead.full_name,
            subject=final_subject, body_html=final_body_html, body_text=final_body_text,
            current_status=EmailStatusEnum.DRAFT, ai_generated=True,
            email_template_id=template.id if template else None,
            personalization_data={"ai_output_id": str(output.id), "ai_job_id": str(output.job_id)},
        )

        fresh_lead = await self.leads.get_by_id(lead.id, organization_id)
        if fresh_lead is not None:
            await self.lead_service.update(
                fresh_lead, payload=LeadUpdateRequest(status=LeadStatusEnum.EMAIL_GENERATED.value), actor=actor
            )

        if was_edited:
            await self.audit_log.record(
                organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email_variant", resource_id=output.id,
                changes={"event": "email_draft_edited_before_approval"},
            )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_variant", resource_id=output.id,
            changes={"event": "email_variant_approved", "email_id": str(email.id)},
        )
        await self.db.commit()
        return await self.emails.get_by_id(email.id, organization_id)  # type: ignore[return-value]

    async def reject_variant(self, organization_id: uuid.UUID, output_id: uuid.UUID, *, actor: User) -> AIOutput:
        output, _lead = await self._require_variant_and_lead(output_id, organization_id)
        await self.ai_outputs.set_approval(output, approved=False, approved_by=actor.id)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_variant", resource_id=output.id,
            changes={"event": "email_variant_rejected"},
        )
        await self.db.commit()
        return output

    async def _require_variant_and_lead(
        self, output_id: uuid.UUID, organization_id: uuid.UUID
    ) -> tuple[AIOutput, Lead]:
        output = await self.ai_outputs.get_by_id(output_id, organization_id)
        if output is None or output.output_type != _OUTPUT_TYPE:
            raise NotFoundError("Email variant not found.")
        job = await self.ai_jobs.get_by_id(output.job_id, organization_id)
        if job is None or job.entity_type != "lead" or job.entity_id is None:
            raise ValidationError("This output is not linked to a lead.")
        lead = await self.require_lead(job.entity_id, organization_id)
        return output, lead

    async def _save_as_template(
        self,
        organization_id: uuid.UUID,
        output: AIOutput,
        lead: Lead,
        content: dict[str, Any],
        actor: User,
        *,
        subject: str,
        body_html: str,
        body_text: str | None,
        template_name: str | None,
    ) -> EmailTemplate:
        template_type = content.get("template_type") or EmailTemplateTypeEnum.COLD_OUTREACH.value
        tone = content.get("tone")
        name = template_name or f"{lead.company_name or lead.full_name} — {template_type}"
        template = await self.templates.create(
            organization_id=organization_id, created_by=actor.id,
            created_by_user_id=actor.id, ai_job_id=output.job_id,
            name=name, template_type=template_type, tone=tone,
            subject=subject, body_html=body_html, body_text=body_text,
            ai_reasoning=content.get("reasoning"),
            variables_used=["first_name", "job_title", "company_name"],
            is_ai_generated=True,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="email_template", resource_id=template.id,
            changes={"event": "email_template_saved_from_ai_output", "ai_output_id": str(output.id)},
        )
        return template

    # ─── Bulk ─────────────────────────────────────────────────────────────────────

    async def bulk_generate(
        self,
        organization_id: uuid.UUID,
        lead_ids: list[str],
        *,
        actor: User,
        template_type: EmailTemplateTypeEnum,
        tone: EmailToneEnum,
        variant_count: int = 2,
    ) -> tuple[int, list[str]]:
        from app.core.config import get_settings

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
                    await self.generate_email(
                        organization_id, lead.id, actor=actor, template_type=template_type,
                        tone=tone, variant_count=variant_count,
                    )
                else:
                    from app.workers.email_tasks import dispatch_lead_email_generation

                    dispatch_lead_email_generation.apply_async(
                        args=[
                            str(lead.id), str(organization_id), str(actor.id),
                            template_type.value, tone.value, variant_count,
                        ],
                        queue="email",
                    )
                queued += 1
            except (ValidationError, NotFoundError) as exc:
                errors.append(f"{lead.id}: {exc}")

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_generation", resource_id=None,
            changes={"event": "bulk_email_generation_triggered", "requested": len(lead_ids), "queued": queued},
        )
        await self.db.commit()
        return queued, errors
