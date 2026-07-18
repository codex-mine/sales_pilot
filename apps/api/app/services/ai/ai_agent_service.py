"""AI Agent configuration CRUD (AI -> Agents)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import json_safe
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import AIAgent
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.repositories.ai_agent_repository import AIAgentRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_repository import PromptRepository
from app.schemas.ai import AIAgentCreateRequest, AIAgentUpdateRequest


class AIAgentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.agents = AIAgentRepository(db)
        self.prompts = PromptRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_agent(self, agent_id: uuid.UUID, organization_id: uuid.UUID) -> AIAgent:
        agent = await self.agents.get_by_id(agent_id, organization_id)
        if agent is None:
            raise NotFoundError("AI agent not found.")
        return agent

    async def _validate_prompt_template(
        self, organization_id: uuid.UUID, template_id: uuid.UUID | None
    ) -> None:
        if template_id is None:
            return
        template = await self.prompts.get_template_by_id(template_id, organization_id)
        if template is None:
            raise ValidationError(
                "Prompt template not found in this organization.",
                errors={"prompt_template_id": ["Invalid template."]},
            )

    async def create(
        self, *, organization_id: uuid.UUID, payload: AIAgentCreateRequest, actor: User
    ) -> AIAgent:
        if await self.agents.get_by_type(organization_id, payload.agent_type.value) is not None:
            raise ValidationError(
                "An agent for this agent type already exists (one per type per organization).",
                errors={"agent_type": ["Already configured."]},
            )
        await self._validate_prompt_template(organization_id, payload.prompt_template_id)
        agent = await self.agents.create(
            organization_id=organization_id, created_by=actor.id, **payload.model_dump()
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="ai_agent", resource_id=agent.id,
        )
        await self.db.commit()
        return await self.agents.get_by_id(agent.id, organization_id)  # type: ignore[return-value]

    async def update(self, agent: AIAgent, *, payload: AIAgentUpdateRequest, actor: User) -> AIAgent:
        changes = payload.model_dump(exclude_unset=True)
        if "prompt_template_id" in changes:
            await self._validate_prompt_template(agent.organization_id, changes["prompt_template_id"])
        before = {f: getattr(agent, f) for f in changes}
        agent = await self.agents.update(agent, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=agent.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_agent", resource_id=agent.id,
            changes={"before": json_safe(before), "after": json_safe(changes)},
        )
        await self.db.commit()
        return await self.agents.get_by_id(agent.id, agent.organization_id)  # type: ignore[return-value]

    async def delete(self, agent: AIAgent, *, actor: User) -> None:
        await self.agents.soft_delete(agent)
        await self.audit_log.record(
            organization_id=agent.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="ai_agent", resource_id=agent.id,
        )
        await self.db.commit()
