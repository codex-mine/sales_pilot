import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai.models import AIAgent


class AIAgentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, agent_id: uuid.UUID, organization_id: uuid.UUID) -> AIAgent | None:
        return await self.db.scalar(
            select(AIAgent)
            .options(selectinload(AIAgent.prompt_template))
            .where(
                AIAgent.id == agent_id,
                AIAgent.organization_id == organization_id,
                AIAgent.deleted_at.is_(None),
            )
        )

    async def get_by_type(self, organization_id: uuid.UUID, agent_type: str) -> AIAgent | None:
        return await self.db.scalar(
            select(AIAgent).where(
                AIAgent.organization_id == organization_id,
                AIAgent.agent_type == agent_type,
                AIAgent.deleted_at.is_(None),
            )
        )

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[AIAgent]:
        result = await self.db.scalars(
            select(AIAgent)
            .options(selectinload(AIAgent.prompt_template))
            .where(AIAgent.organization_id == organization_id, AIAgent.deleted_at.is_(None))
            .order_by(AIAgent.agent_type)
        )
        return list(result)

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> AIAgent:
        agent = AIAgent(organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields)
        self.db.add(agent)
        await self.db.flush()
        return agent

    async def update(self, agent: AIAgent, changes: dict[str, Any], *, updated_by: uuid.UUID | None) -> AIAgent:
        for f, v in changes.items():
            setattr(agent, f, v)
        agent.updated_by = updated_by
        await self.db.flush()
        return agent

    async def soft_delete(self, agent: AIAgent) -> None:
        agent.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
