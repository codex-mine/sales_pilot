"""
The single execution chokepoint for every LLM call in the system.

Feature modules (research, email generation, reply classification, meeting
detection) call `AIJobService.run_job(...)` and poll the returned job — they
never import an LLM SDK, compute cost, or handle retries themselves.

Execution model:
- `run_job` resolves agent + prompt, inserts the PENDING AIJob row, commits,
  then dispatches `execute_ai_job` to the Celery `ai` queue (or awaits it
  inline when `ai_execute_jobs_eagerly` is set — dev/test only).
- `execute_job` is the worker-side body: RUNNING -> provider call -> COMPLETED
  (with AIOutput + token/cost/latency accounting) or FAILED. Celery-level
  retry (`app/workers/ai_tasks.py`) re-invokes it after bumping retry_count.
- Endpoint-triggered "retry" of a FAILED job is orchestrated: it creates a
  NEW job with parent_job_id pointing at the original, per the model's
  append-only audit rule.
"""

import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import get_graph_builder
from app.agents.base import checkpointer_context
from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import AIJob, AIOutput
from app.models.enums import AIAgentTypeEnum, AIJobStatusEnum, AuditActionEnum, LLMProviderEnum
from app.models.identity.models import User
from app.repositories.ai_agent_repository import AIAgentRepository
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.ai_output_repository import AIOutputRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_repository import PromptRepository
from app.services.ai.ai_settings_service import AISettingsService
from app.services.ai.cost_tracking_callback import CostTrackingCallbackHandler
from app.services.ai.prompt_service import PromptService, render_prompt
from app.services.ai.system_prompts import SYSTEM_PROMPT_TEMPLATES

_TERMINAL_STATUSES = {
    AIJobStatusEnum.COMPLETED,
    AIJobStatusEnum.FAILED,
    AIJobStatusEnum.CANCELLED,
}


class AIJobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.jobs = AIJobRepository(db)
        self.agents = AIAgentRepository(db)
        self.outputs = AIOutputRepository(db)
        self.prompts = PromptRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.settings_service = AISettingsService(db)

    async def require_job(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> AIJob:
        job = await self.jobs.get_by_id(job_id, organization_id)
        if job is None:
            raise NotFoundError("AI job not found.")
        return job

    # ─── The chokepoint ───────────────────────────────────────────────────────

    async def run_job(
        self,
        *,
        organization_id: uuid.UUID,
        job_type: str,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        prompt_template_name: str,
        variables: dict,
        agent_type: AIAgentTypeEnum,
        initiated_by: uuid.UUID | None,
        parent_job_id: uuid.UUID | None = None,
        response_format: str = "text",
    ) -> AIJob:
        settings = get_settings()

        # 1. Resolve the org's agent config for this type, falling back to the
        #    platform default when none is configured.
        agent = await self.agents.get_by_type(organization_id, agent_type.value)
        provider = agent.provider if agent else LLMProviderEnum(settings.ai_default_provider)
        model_name = agent.model_name if agent else settings.ai_default_model
        temperature = agent.temperature if agent else settings.ai_default_temperature
        max_tokens = agent.max_tokens if agent else settings.ai_default_max_tokens
        if agent is not None and not agent.is_active:
            raise ValidationError(f"The '{agent_type.value}' agent is disabled.")

        # 2. Resolve the active prompt version, lazily seeding system templates
        #    for organizations created before this module existed.
        resolved = await self.prompts.get_active_version(organization_id, prompt_template_name)
        if resolved is None:
            await PromptService(self.db).ensure_system_templates(organization_id)
            resolved = await self.prompts.get_active_version(organization_id, prompt_template_name)
        if resolved is None:
            raise NotFoundError(f"No active prompt version for template '{prompt_template_name}'.")
        _template, version = resolved

        # Render now so a missing variable fails the request immediately, and
        # store the rendered payload for exact replay.
        system_prompt, user_prompt = render_prompt(version, variables)

        # 3. Insert the PENDING job with the full input payload.
        job = await self.jobs.create(
            organization_id=organization_id,
            job_type=job_type,
            agent_id=agent.id if agent else None,
            entity_type=entity_type,
            entity_id=entity_id,
            initiated_by=initiated_by,
            parent_job_id=parent_job_id,
            provider=provider,
            model_name=model_name,
            prompt_version_id=version.id,
            input_data={
                "prompt_template": prompt_template_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "variables": _stringify_values(variables),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format,
            },
            max_retries=settings.ai_max_retries,
        )
        await self.db.commit()

        # 4. Dispatch. Eager mode executes inline (dev/test without a worker);
        #    otherwise the Celery `ai` queue picks it up.
        if settings.ai_execute_jobs_eagerly:
            await self.execute_job(job.id, organization_id)
        else:
            from app.workers.ai_tasks import execute_ai_job

            task = execute_ai_job.apply_async(
                args=[str(job.id), str(organization_id)], queue="ai"
            )
            job = await self.require_job(job.id, organization_id)
            job.celery_task_id = task.id
            await self.db.commit()

        # 5. Return the (PENDING/RUNNING or, in eager mode, terminal) row.
        return await self.require_job(job.id, organization_id)

    # ─── Worker-side execution body ───────────────────────────────────────────

    async def execute_job(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> AIJob:
        job = await self.require_job(job_id, organization_id)
        if job.status in _TERMINAL_STATUSES:
            # Idempotency guard: a redelivered/duplicate task must not re-run
            # a finished job.
            return job

        await self.jobs.mark_running(job)
        await self.db.commit()

        input_data = job.input_data or {}
        started = time.monotonic()
        cost_handler = CostTrackingCallbackHandler()
        provider = LLMProviderEnum(job.provider)
        try:
            api_key, base_url = await self.settings_service.resolve_credentials(organization_id, provider)
            agent_type = _resolve_agent_type(job)
            initial_state = _build_initial_state(job, input_data, provider, api_key, base_url)

            # A fresh checkpointer + compiled graph per invocation — see
            # app/agents/base.py's module docstring for why (Celery's
            # fresh-event-loop-per-task-run constraint applies to the
            # checkpointer's DB connection exactly like it does to the
            # session engine `run_with_fresh_session` builds per call).
            async with checkpointer_context() as checkpointer:
                graph = get_graph_builder(agent_type)().compile(checkpointer=checkpointer)
                final_state = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": str(job.id)}, "callbacks": [cost_handler]},
                )
            output_content = final_state.get("output_content") or ""
            output_json = final_state.get("output_json")
        except Exception as exc:  # noqa: BLE001 — every failure lands on the job row
            await self.jobs.mark_failed(
                job, error_message=str(exc), error_traceback=traceback.format_exc()
            )
            await self._audit_system_event(job, "ai_job_failed", {"error": str(exc)})
            await self.db.commit()
            raise

        latency_ms = int((time.monotonic() - started) * 1000)
        await self.outputs.create(
            job_id=job.id,
            organization_id=organization_id,
            output_type=job.job_type,
            content_text=output_content,
            content_json=output_json,
        )
        await self.jobs.mark_completed(
            job,
            input_tokens=cost_handler.input_tokens,
            output_tokens=cost_handler.output_tokens,
            cost_usd=cost_handler.cost_usd(provider, job.model_name or ""),
            latency_ms=latency_ms,
        )
        await self._audit_system_event(job, "ai_job_completed", {"cost_usd": job.cost_usd})
        await self.db.commit()
        return await self.require_job(job.id, organization_id)

    async def mark_retrying(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        """Called by the Celery retry hook between attempts."""
        job = await self.require_job(job_id, organization_id)
        await self.jobs.mark_retrying(job)
        await self.db.commit()

    # ─── Endpoint actions ─────────────────────────────────────────────────────

    async def retry_job(self, job: AIJob, *, actor: User) -> AIJob:
        """Orchestrated retry: a FAILED/CANCELLED job is never mutated back to
        life — a new job row is created with parent_job_id linking the chain."""
        if job.status not in {AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}:
            raise ValidationError("Only failed or cancelled jobs can be retried.")
        input_data = job.input_data or {}
        template_name = input_data.get("prompt_template")
        if not template_name:
            raise ValidationError("This job has no stored prompt template and cannot be retried.")
        agent_type = job.agent.agent_type if job.agent else AIAgentTypeEnum.ORCHESTRATOR
        new_job = await self.run_job(
            organization_id=job.organization_id,
            job_type=job.job_type,
            entity_type=job.entity_type,
            entity_id=job.entity_id,
            prompt_template_name=template_name,
            variables=input_data.get("variables", {}),
            agent_type=AIAgentTypeEnum(agent_type),
            initiated_by=actor.id,
            parent_job_id=job.id,
        )
        await self.audit_log.record(
            organization_id=job.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_job", resource_id=job.id,
            changes={"action": "retried", "new_job_id": str(new_job.id)},
        )
        await self.db.commit()
        return new_job

    async def cancel_job(self, job: AIJob, *, actor: User) -> AIJob:
        if job.status in _TERMINAL_STATUSES:
            raise ValidationError("This job has already finished.")
        await self.jobs.mark_cancelled(job)
        await self.audit_log.record(
            organization_id=job.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_job", resource_id=job.id,
            changes={"action": "cancelled"},
        )
        await self.db.commit()
        return await self.require_job(job.id, job.organization_id)

    async def set_output_approval(
        self, output: AIOutput, *, approved: bool, actor: User
    ) -> AIOutput:
        await self.outputs.set_approval(output, approved=approved, approved_by=actor.id)
        await self.audit_log.record(
            organization_id=output.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_output", resource_id=output.id,
            changes={"is_approved": approved},
        )
        await self.db.commit()
        return output

    async def require_output(self, output_id: uuid.UUID, organization_id: uuid.UUID) -> AIOutput:
        output = await self.outputs.get_by_id(output_id, organization_id)
        if output is None:
            raise NotFoundError("AI output not found.")
        return output

    # ─── Usage ────────────────────────────────────────────────────────────────

    async def usage(self, organization_id: uuid.UUID, *, days: int = 30) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        by_job_type = await self.jobs.usage_summary(organization_id, since=since)
        daily = await self.jobs.daily_costs(organization_id, since=since)
        all_time = await self.jobs.usage_summary(organization_id)
        return {
            "window_days": days,
            "total_cost_usd": round(sum(row["cost_usd"] for row in by_job_type), 6),
            "total_jobs": sum(row["job_count"] for row in by_job_type),
            "total_tokens": sum(row["total_tokens"] for row in by_job_type),
            "all_time_cost_usd": round(sum(row["cost_usd"] for row in all_time), 6),
            "by_job_type": by_job_type,
            "daily_costs": daily,
        }

    # ─── Internals ────────────────────────────────────────────────────────────

    async def _audit_system_event(self, job: AIJob, action_detail: str, extra: dict) -> None:
        """System-actor audit entries for job lifecycle events (actor NULL per
        the AuditLog convention for automated actions)."""
        await self.audit_log.record(
            organization_id=job.organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.UPDATE, resource_type="ai_job", resource_id=job.id,
            changes={"event": action_detail, **_stringify_values(extra)},
        )


def _resolve_agent_type(job: AIJob) -> AIAgentTypeEnum:
    """AIJob has no `agent_type` column of its own (only `agent_id`, which is
    NULL whenever an org runs on the platform-default agent config rather
    than an explicit `AIAgent` row) — the system prompt template name stored
    in `input_data` is the reliable source, since every current caller
    (CompanyResearchService, EmailGenerationService, InboundEmailService,
    ProspectAnalysisService) always passes one of the five fixed system
    template names. Falls back to `job.agent.agent_type`, then
    `ORCHESTRATOR`, mirroring `retry_job`'s existing fallback chain."""
    template_name = (job.input_data or {}).get("prompt_template")
    seed = SYSTEM_PROMPT_TEMPLATES.get(template_name) if template_name else None
    if seed is not None:
        return seed[0]
    if job.agent is not None:
        return AIAgentTypeEnum(job.agent.agent_type)
    return AIAgentTypeEnum.ORCHESTRATOR


def _build_initial_state(
    job: AIJob, input_data: dict, provider: LLMProviderEnum, api_key: str | None, base_url: str | None
) -> dict:
    """One shared superset state dict for every graph — each graph's own
    `TypedDict` schema only reads the keys it declares, so passing the full
    set here (rather than branching per agent type) keeps this call site
    simple without any graph seeing fields it doesn't understand."""
    variables = input_data.get("variables") or {}
    return {
        "job_id": job.id,
        "system_prompt": input_data.get("system_prompt", ""),
        "user_prompt": input_data.get("user_prompt", ""),
        "provider": provider.value,
        "model_name": job.model_name or "",
        "temperature": input_data.get("temperature", 0.7),
        "max_tokens": input_data.get("max_tokens", 2048),
        "api_key": api_key,
        "base_url": base_url,
        "response_format": input_data.get("response_format", "text"),
        "reply_body": variables.get("reply_body"),
        "company_name": variables.get("company_name"),
        "data_quality": variables.get("data_quality"),
        "variants": None,
        "critique_passed": None,
        "critique_feedback": None,
        "critique_attempts": 0,
        "classification": None,
        "meeting_intent": None,
        "output_content": None,
        "output_json": None,
    }


def _stringify_values(payload: dict) -> dict:
    """input_data / audit changes are JSONB — coerce UUIDs and other non-JSON
    values to strings without importing the service-layer helper circularly."""
    from app.core.utils import json_safe

    return json_safe(payload)
