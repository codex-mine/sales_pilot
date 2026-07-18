"""
Prompt Template + Version management (AI -> Prompts).

PromptVersion rows are immutable: "editing" a prompt is always creating
version N+1 and pointing `active_version_id` at it. Rendering validates the
caller's variables against the version's declared variable list up front so
a missing variable is a clear ValidationError, not a Jinja2 UndefinedError
mid-render.
"""

import uuid
from typing import Any

from jinja2 import Environment, StrictUndefined
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import json_safe
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import PromptTemplate, PromptVersion
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_repository import PromptRepository
from app.schemas.ai import (
    PromptTemplateCreateRequest,
    PromptTemplateUpdateRequest,
    PromptVersionCreateRequest,
)
from app.services.ai.system_prompts import SYSTEM_PROMPT_TEMPLATES

_jinja = Environment(undefined=StrictUndefined, autoescape=False)


def render_prompt(version: PromptVersion, variables: dict[str, Any]) -> tuple[str, str]:
    """Returns (system_prompt, rendered_user_prompt). Validates declared
    variables before rendering."""
    declared = set(version.variables or [])
    missing = sorted(declared - set(variables))
    if missing:
        raise ValidationError(
            f"Missing prompt variables: {', '.join(missing)}.",
            errors={"variables": [f"Missing: {name}" for name in missing]},
        )
    rendered = _jinja.from_string(version.user_prompt_template).render(**variables)
    return version.system_prompt, rendered


class PromptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.prompts = PromptRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_template(self, template_id: uuid.UUID, organization_id: uuid.UUID) -> PromptTemplate:
        template = await self.prompts.get_template_by_id(template_id, organization_id)
        if template is None:
            raise NotFoundError("Prompt template not found.")
        return template

    # ─── System template seeding ──────────────────────────────────────────────

    async def ensure_system_templates(self, organization_id: uuid.UUID) -> None:
        """Idempotently creates any missing system templates (+ initial active
        version) for the organization. Called at org creation and lazily from
        AIJobService for organizations created before this module existed."""
        for name, (agent_type, description, system_prompt, user_template, variables) in (
            SYSTEM_PROMPT_TEMPLATES.items()
        ):
            existing = await self.prompts.get_template_by_name(organization_id, name)
            if existing is not None:
                continue
            template = await self.prompts.create_template(
                organization_id=organization_id,
                created_by=None,
                name=name,
                agent_type=agent_type,
                description=description,
                is_system=True,
            )
            version = await self.prompts.create_version(
                template_id=template.id,
                organization_id=organization_id,
                created_by=None,
                system_prompt=system_prompt,
                user_prompt_template=user_template,
                variables=variables,
                change_notes="Initial system version.",
            )
            template.active_version_id = version.id
        await self.db.flush()

    # ─── Template CRUD ────────────────────────────────────────────────────────

    async def create_template(
        self, *, organization_id: uuid.UUID, payload: PromptTemplateCreateRequest, actor: User
    ) -> PromptTemplate:
        if await self.prompts.get_template_by_name(organization_id, payload.name) is not None:
            raise ValidationError(
                "A prompt template with this name already exists.",
                errors={"name": ["Already in use."]},
            )
        template = await self.prompts.create_template(
            organization_id=organization_id,
            created_by=actor.id,
            name=payload.name,
            agent_type=payload.agent_type,
            description=payload.description,
            is_system=False,
        )
        version = await self.prompts.create_version(
            template_id=template.id,
            organization_id=organization_id,
            created_by=actor.id,
            system_prompt=payload.system_prompt,
            user_prompt_template=payload.user_prompt_template,
            variables=payload.variables,
            change_notes="Initial version.",
        )
        template.active_version_id = version.id
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="prompt_template", resource_id=template.id,
        )
        await self.db.commit()
        return await self.prompts.get_template_by_id(template.id, organization_id)  # type: ignore[return-value]

    async def update_template(
        self, template: PromptTemplate, *, payload: PromptTemplateUpdateRequest, actor: User
    ) -> PromptTemplate:
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and template.is_system:
            raise ValidationError("System templates cannot be renamed.")
        if "name" in changes and changes["name"] != template.name:
            if await self.prompts.get_template_by_name(template.organization_id, changes["name"]) is not None:
                raise ValidationError(
                    "A prompt template with this name already exists.",
                    errors={"name": ["Already in use."]},
                )
        before = {f: getattr(template, f) for f in changes}
        template = await self.prompts.update_template(template, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=template.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="prompt_template", resource_id=template.id,
            changes={"before": json_safe(before), "after": json_safe(changes)},
        )
        await self.db.commit()
        return await self.prompts.get_template_by_id(template.id, template.organization_id)  # type: ignore[return-value]

    # ─── Versions ─────────────────────────────────────────────────────────────

    async def create_version(
        self, template: PromptTemplate, *, payload: PromptVersionCreateRequest, actor: User
    ) -> PromptVersion:
        version = await self.prompts.create_version(
            template_id=template.id,
            organization_id=template.organization_id,
            created_by=actor.id,
            system_prompt=payload.system_prompt,
            user_prompt_template=payload.user_prompt_template,
            variables=payload.variables,
            provider=payload.provider,
            model_name=payload.model_name,
            temperature=payload.temperature,
            change_notes=payload.change_notes,
        )
        if payload.activate:
            template.active_version_id = version.id
            template.updated_by = actor.id
        await self.audit_log.record(
            organization_id=template.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="prompt_version", resource_id=version.id,
            changes={"template_id": str(template.id), "version_number": version.version_number,
                     "activated": payload.activate},
        )
        await self.db.commit()
        return version

    async def activate_version(
        self, template: PromptTemplate, version_id: uuid.UUID, *, actor: User
    ) -> PromptTemplate:
        version = await self.prompts.get_version_by_id(version_id, template.organization_id)
        if version is None or version.template_id != template.id:
            raise NotFoundError("Prompt version not found.")
        previous = template.active_version_id
        template.active_version_id = version.id
        template.updated_by = actor.id
        await self.db.flush()
        await self.audit_log.record(
            organization_id=template.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="prompt_template", resource_id=template.id,
            changes={
                "before": {"active_version_id": str(previous) if previous else None},
                "after": {"active_version_id": str(version.id)},
            },
        )
        await self.db.commit()
        return await self.prompts.get_template_by_id(template.id, template.organization_id)  # type: ignore[return-value]
