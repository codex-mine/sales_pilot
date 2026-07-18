import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai.models import ProspectAnalysis


class ProspectAnalysisRepository:
    """`lead_id` is unique — same upsert-in-place pattern as
    CompanyResearchRepository. History lives on AIJob rows
    (entity_type='lead', job_type='analyze_prospect')."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_lead(
        self, lead_id: uuid.UUID, organization_id: uuid.UUID
    ) -> ProspectAnalysis | None:
        return await self.db.scalar(
            select(ProspectAnalysis).where(
                ProspectAnalysis.lead_id == lead_id,
                ProspectAnalysis.organization_id == organization_id,
            )
        )

    async def upsert(
        self, *, lead_id: uuid.UUID, organization_id: uuid.UUID, **fields: Any
    ) -> ProspectAnalysis:
        existing = await self.get_by_lead(lead_id, organization_id)
        now = datetime.now(timezone.utc)
        if existing is not None:
            for field, value in fields.items():
                setattr(existing, field, value)
            existing.analysed_at = now
            await self.db.flush()
            return existing
        analysis = ProspectAnalysis(
            lead_id=lead_id, organization_id=organization_id, analysed_at=now, **fields
        )
        self.db.add(analysis)
        await self.db.flush()
        return analysis
