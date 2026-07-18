import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai.models import CompanyResearch


class CompanyResearchRepository:
    """`company_id` is unique — only the latest research survives here.
    History lives on AIJob rows (entity_type='company',
    job_type='research_company'); `upsert` is how "re-research" overwrites
    the current profile while that history keeps accumulating."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_company(
        self, company_id: uuid.UUID, organization_id: uuid.UUID
    ) -> CompanyResearch | None:
        return await self.db.scalar(
            select(CompanyResearch).where(
                CompanyResearch.company_id == company_id,
                CompanyResearch.organization_id == organization_id,
            )
        )

    async def upsert(
        self, *, company_id: uuid.UUID, organization_id: uuid.UUID, **fields: Any
    ) -> CompanyResearch:
        existing = await self.get_by_company(company_id, organization_id)
        now = datetime.now(timezone.utc)
        if existing is not None:
            for field, value in fields.items():
                setattr(existing, field, value)
            existing.researched_at = now
            await self.db.flush()
            return existing
        research = CompanyResearch(
            company_id=company_id, organization_id=organization_id, researched_at=now, **fields
        )
        self.db.add(research)
        await self.db.flush()
        return research
