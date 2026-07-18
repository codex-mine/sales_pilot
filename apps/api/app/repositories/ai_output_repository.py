import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai.models import AIOutput


class AIOutputRepository:
    """AIOutput content is immutable once written — the only mutation this
    repository exposes is the approval tri-state (is_approved/approved_by/
    approved_at), per the model's docstring."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, output_id: uuid.UUID, organization_id: uuid.UUID) -> AIOutput | None:
        return await self.db.scalar(
            select(AIOutput).where(
                AIOutput.id == output_id, AIOutput.organization_id == organization_id
            )
        )

    async def create(
        self,
        *,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
        output_type: str,
        content_text: str | None = None,
        content_json: dict | list | None = None,
        quality_score: float | None = None,
    ) -> AIOutput:
        output = AIOutput(
            job_id=job_id,
            organization_id=organization_id,
            output_type=output_type,
            content_text=content_text,
            content_json=content_json,
            quality_score=quality_score,
        )
        self.db.add(output)
        await self.db.flush()
        return output

    async def set_approval(self, output: AIOutput, *, approved: bool, approved_by: uuid.UUID) -> AIOutput:
        output.is_approved = approved
        output.approved_by = approved_by
        output.approved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return output
