"""ORM -> response-schema mapping for the AI module."""

import enum

from app.models.ai.models import AIAgent, AIJob, AIOutput, PromptTemplate, PromptVersion
from app.schemas.ai import (
    AIAgentResponse,
    AIJobListItemResponse,
    AIJobResponse,
    AIOutputResponse,
    PromptTemplateResponse,
    PromptVersionResponse,
)


def _ev(value):
    """Enum-safe string: a freshly-created row still holds the enum instance
    (str() of a mixed-in (str, Enum) gives 'Class.MEMBER', not the value);
    a DB-loaded row holds the plain string. Normalize both to the value."""
    if value is None:
        return None
    return value.value if isinstance(value, enum.Enum) else str(value)


def serialize_agent(agent: AIAgent) -> AIAgentResponse:
    return AIAgentResponse(
        id=str(agent.id),
        organization_id=str(agent.organization_id),
        name=agent.name,
        agent_type=_ev(agent.agent_type),
        description=agent.description,
        provider=_ev(agent.provider),
        model_name=agent.model_name,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        prompt_template_id=str(agent.prompt_template_id) if agent.prompt_template_id else None,
        prompt_template_name=agent.prompt_template.name if agent.prompt_template else None,
        is_active=agent.is_active,
        config=agent.config,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def serialize_output(output: AIOutput) -> AIOutputResponse:
    return AIOutputResponse(
        id=str(output.id),
        job_id=str(output.job_id),
        output_type=output.output_type,
        content_text=output.content_text,
        content_json=output.content_json,
        is_approved=output.is_approved,
        approved_by=str(output.approved_by) if output.approved_by else None,
        approved_at=output.approved_at,
        quality_score=output.quality_score,
        created_at=output.created_at,
    )


def serialize_job(job: AIJob) -> AIJobResponse:
    return AIJobResponse(
        id=str(job.id),
        organization_id=str(job.organization_id),
        agent_id=str(job.agent_id) if job.agent_id else None,
        agent_type=_ev(job.agent.agent_type) if job.agent else None,
        parent_job_id=str(job.parent_job_id) if job.parent_job_id else None,
        initiated_by=str(job.initiated_by) if job.initiated_by else None,
        entity_type=job.entity_type,
        entity_id=str(job.entity_id) if job.entity_id else None,
        job_type=job.job_type,
        status=_ev(job.status),
        provider=_ev(job.provider),
        model_name=job.model_name,
        prompt_version_id=str(job.prompt_version_id) if job.prompt_version_id else None,
        input_data=job.input_data,
        error_message=job.error_message,
        input_tokens=job.input_tokens,
        output_tokens=job.output_tokens,
        total_tokens=job.total_tokens,
        cost_usd=job.cost_usd,
        latency_ms=job.latency_ms,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        outputs=[serialize_output(o) for o in job.outputs],
    )


def serialize_job_list_item(job: AIJob) -> AIJobListItemResponse:
    return AIJobListItemResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=_ev(job.status),
        entity_type=job.entity_type,
        entity_id=str(job.entity_id) if job.entity_id else None,
        provider=_ev(job.provider),
        model_name=job.model_name,
        total_tokens=job.total_tokens,
        cost_usd=job.cost_usd,
        latency_ms=job.latency_ms,
        retry_count=job.retry_count,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


def serialize_template(
    template: PromptTemplate, *, version_count: int, active_version_number: int | None
) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=str(template.id),
        organization_id=str(template.organization_id),
        name=template.name,
        agent_type=_ev(template.agent_type),
        description=template.description,
        is_system=template.is_system,
        active_version_id=str(template.active_version_id) if template.active_version_id else None,
        active_version_number=active_version_number,
        version_count=version_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def serialize_version(version: PromptVersion, *, is_active: bool) -> PromptVersionResponse:
    return PromptVersionResponse(
        id=str(version.id),
        template_id=str(version.template_id),
        version_number=version.version_number,
        system_prompt=version.system_prompt,
        user_prompt_template=version.user_prompt_template,
        variables=list(version.variables or []),
        provider=_ev(version.provider),
        model_name=version.model_name,
        temperature=version.temperature,
        change_notes=version.change_notes,
        is_active=is_active,
        total_uses=version.total_uses,
        created_at=version.created_at,
    )
