"""AI Provider Foundation routes (AI -> Agents / Jobs / Outputs / Prompts /
Settings / Usage)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.config import get_settings
from app.database.session import get_db
from app.models.identity.models import User
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.prompt_repository import PromptRepository
from app.schemas.ai import (
    AIAgentCreateRequest,
    AIAgentResponse,
    AIAgentUpdateRequest,
    AIJobListItemResponse,
    AIJobResponse,
    AIOutputResponse,
    AISettingsResponse,
    AISettingsUpdateRequest,
    AIUsageResponse,
    PromptTemplateCreateRequest,
    PromptTemplateResponse,
    PromptTemplateUpdateRequest,
    PromptVersionCreateRequest,
    PromptVersionResponse,
)
from app.schemas.ai_serializers import (
    serialize_agent,
    serialize_job,
    serialize_job_list_item,
    serialize_output,
    serialize_template,
    serialize_version,
)
from app.schemas.common import ApiResponse
from app.services.ai.ai_agent_service import AIAgentService
from app.services.ai.ai_job_service import AIJobService
from app.services.ai.ai_settings_service import AISettingsService
from app.services.ai.prompt_service import PromptService

router = APIRouter(prefix="/ai", tags=["ai"])

# NOTE ON ROUTE ORDER: static-string segments (/jobs, /outputs, /settings,
# /usage, /prompt-templates) all live under distinct prefixes here, and every
# parameterized segment is namespaced (e.g. /agents/{agent_id}), so the
# companies.py UUID-misrouting failure mode can't occur — but keep any future
# static /agents/... routes ABOVE /agents/{agent_id} all the same.


async def _serialize_template_full(template, db: AsyncSession) -> PromptTemplateResponse:
    versions = await PromptRepository(db).list_versions(template.id)
    active_number = next(
        (v.version_number for v in versions if v.id == template.active_version_id), None
    )
    return serialize_template(template, version_count=len(versions), active_version_number=active_number)


# ─── Agents ────────────────────────────────────────────────────────────────────


@router.get("/agents", response_model=ApiResponse[list[AIAgentResponse]])
async def list_agents(
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AIAgentResponse]]:
    agents = await AIAgentService(db).agents.list_for_organization(user.organization_id)
    return ApiResponse(data=[serialize_agent(a) for a in agents])


@router.post("/agents", response_model=ApiResponse[AIAgentResponse], status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AIAgentCreateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIAgentResponse]:
    agent = await AIAgentService(db).create(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    return ApiResponse(data=serialize_agent(agent), message="AI agent created.")


@router.get("/agents/{agent_id}", response_model=ApiResponse[AIAgentResponse])
async def get_agent(
    agent_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIAgentResponse]:
    agent = await AIAgentService(db).require_agent(agent_id, user.organization_id)
    return ApiResponse(data=serialize_agent(agent))


@router.patch("/agents/{agent_id}", response_model=ApiResponse[AIAgentResponse])
async def update_agent(
    agent_id: uuid.UUID,
    payload: AIAgentUpdateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIAgentResponse]:
    service = AIAgentService(db)
    agent = await service.require_agent(agent_id, user.organization_id)
    agent = await service.update(agent, payload=payload, actor=user)
    return ApiResponse(data=serialize_agent(agent), message="AI agent updated.")


@router.delete("/agents/{agent_id}", response_model=ApiResponse[None])
async def delete_agent(
    agent_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = AIAgentService(db)
    agent = await service.require_agent(agent_id, user.organization_id)
    await service.delete(agent, actor=user)
    return ApiResponse(data=None, message="AI agent deleted.")


# ─── Jobs ──────────────────────────────────────────────────────────────────────


@router.get("/jobs", response_model=ApiResponse[list[AIJobListItemResponse]])
async def list_jobs(
    status_filter: list[str] | None = Query(default=None, alias="status"),
    job_type: list[str] | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AIJobListItemResponse]]:
    jobs, total = await AIJobRepository(db).list_for_organization(
        user.organization_id,
        status=status_filter,
        job_type=job_type,
        entity_type=entity_type,
        entity_id=entity_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=[serialize_job_list_item(j) for j in jobs],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/jobs/{job_id}", response_model=ApiResponse[AIJobResponse])
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIJobResponse]:
    job = await AIJobService(db).require_job(job_id, user.organization_id)
    return ApiResponse(data=serialize_job(job))


@router.post("/jobs/{job_id}/retry", response_model=ApiResponse[AIJobResponse])
async def retry_job(
    job_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIJobResponse]:
    service = AIJobService(db)
    job = await service.require_job(job_id, user.organization_id)
    new_job = await service.retry_job(job, actor=user)
    return ApiResponse(data=serialize_job(new_job), message="Retry started as a new job.")


@router.post("/jobs/{job_id}/cancel", response_model=ApiResponse[AIJobResponse])
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIJobResponse]:
    service = AIJobService(db)
    job = await service.require_job(job_id, user.organization_id)
    job = await service.cancel_job(job, actor=user)
    return ApiResponse(data=serialize_job(job), message="Job cancelled.")


# ─── Outputs ───────────────────────────────────────────────────────────────────


@router.get("/outputs/{output_id}", response_model=ApiResponse[AIOutputResponse])
async def get_output(
    output_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIOutputResponse]:
    output = await AIJobService(db).require_output(output_id, user.organization_id)
    return ApiResponse(data=serialize_output(output))


@router.post("/outputs/{output_id}/approve", response_model=ApiResponse[AIOutputResponse])
async def approve_output(
    output_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIOutputResponse]:
    service = AIJobService(db)
    output = await service.require_output(output_id, user.organization_id)
    output = await service.set_output_approval(output, approved=True, actor=user)
    return ApiResponse(data=serialize_output(output), message="Output approved.")


@router.post("/outputs/{output_id}/reject", response_model=ApiResponse[AIOutputResponse])
async def reject_output(
    output_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIOutputResponse]:
    service = AIJobService(db)
    output = await service.require_output(output_id, user.organization_id)
    output = await service.set_output_approval(output, approved=False, actor=user)
    return ApiResponse(data=serialize_output(output), message="Output rejected.")


# ─── Prompt templates / versions ───────────────────────────────────────────────


@router.get("/prompt-templates", response_model=ApiResponse[list[PromptTemplateResponse]])
async def list_prompt_templates(
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PromptTemplateResponse]]:
    service = PromptService(db)
    # Lazy backfill so orgs created before this module still see the system set.
    await service.ensure_system_templates(user.organization_id)
    await db.commit()
    templates = await service.prompts.list_templates(user.organization_id)
    data = [await _serialize_template_full(t, db) for t in templates]
    return ApiResponse(data=data)


@router.post(
    "/prompt-templates",
    response_model=ApiResponse[PromptTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_template(
    payload: PromptTemplateCreateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PromptTemplateResponse]:
    template = await PromptService(db).create_template(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    return ApiResponse(data=await _serialize_template_full(template, db), message="Prompt template created.")


@router.get("/prompt-templates/{template_id}", response_model=ApiResponse[PromptTemplateResponse])
async def get_prompt_template(
    template_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PromptTemplateResponse]:
    template = await PromptService(db).require_template(template_id, user.organization_id)
    return ApiResponse(data=await _serialize_template_full(template, db))


@router.patch("/prompt-templates/{template_id}", response_model=ApiResponse[PromptTemplateResponse])
async def update_prompt_template(
    template_id: uuid.UUID,
    payload: PromptTemplateUpdateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PromptTemplateResponse]:
    service = PromptService(db)
    template = await service.require_template(template_id, user.organization_id)
    template = await service.update_template(template, payload=payload, actor=user)
    return ApiResponse(data=await _serialize_template_full(template, db), message="Prompt template updated.")


@router.get(
    "/prompt-templates/{template_id}/versions",
    response_model=ApiResponse[list[PromptVersionResponse]],
)
async def list_prompt_versions(
    template_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PromptVersionResponse]]:
    service = PromptService(db)
    template = await service.require_template(template_id, user.organization_id)
    versions = await service.prompts.list_versions(template.id)
    return ApiResponse(
        data=[serialize_version(v, is_active=v.id == template.active_version_id) for v in versions]
    )


@router.post(
    "/prompt-templates/{template_id}/versions",
    response_model=ApiResponse[PromptVersionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    template_id: uuid.UUID,
    payload: PromptVersionCreateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PromptVersionResponse]:
    service = PromptService(db)
    template = await service.require_template(template_id, user.organization_id)
    version = await service.create_version(template, payload=payload, actor=user)
    template = await service.require_template(template_id, user.organization_id)
    return ApiResponse(
        data=serialize_version(version, is_active=version.id == template.active_version_id),
        message="Prompt version created.",
    )


@router.post(
    "/prompt-templates/{template_id}/versions/{version_id}/activate",
    response_model=ApiResponse[PromptTemplateResponse],
)
async def activate_prompt_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PromptTemplateResponse]:
    service = PromptService(db)
    template = await service.require_template(template_id, user.organization_id)
    template = await service.activate_version(template, version_id, actor=user)
    return ApiResponse(data=await _serialize_template_full(template, db), message="Version activated.")


# ─── Usage / settings ──────────────────────────────────────────────────────────


@router.get("/usage", response_model=ApiResponse[AIUsageResponse])
async def get_usage(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_permission("ai", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIUsageResponse]:
    usage = await AIJobService(db).usage(user.organization_id, days=days)
    return ApiResponse(data=AIUsageResponse(**usage))


@router.get("/settings", response_model=ApiResponse[AISettingsResponse])
async def get_ai_settings(
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AISettingsResponse]:
    statuses = await AISettingsService(db).provider_statuses(user.organization_id)
    settings = get_settings()
    return ApiResponse(
        data=AISettingsResponse(
            providers=statuses,
            default_provider=settings.ai_default_provider,
            default_model=settings.ai_default_model,
        )
    )


@router.patch("/settings", response_model=ApiResponse[AISettingsResponse])
async def update_ai_settings(
    payload: AISettingsUpdateRequest,
    user: User = Depends(require_permission("ai", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AISettingsResponse]:
    service = AISettingsService(db)
    if payload.remove:
        await service.remove_provider_key(
            organization_id=user.organization_id, provider=payload.provider, actor=user
        )
        message = "Provider credentials removed."
    else:
        await service.set_provider_key(
            organization_id=user.organization_id,
            provider=payload.provider,
            api_key=payload.api_key,
            base_url=payload.base_url,
            actor=user,
        )
        message = "Provider credentials saved."
    statuses = await service.provider_statuses(user.organization_id)
    settings = get_settings()
    return ApiResponse(
        data=AISettingsResponse(
            providers=statuses,
            default_provider=settings.ai_default_provider,
            default_model=settings.ai_default_model,
        ),
        message=message,
    )
