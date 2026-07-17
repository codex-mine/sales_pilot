import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm.models import Activity
from app.models.enums import ActivityTypeEnum


class ActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        activity_type: ActivityTypeEnum,
        lead_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        summary: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> Activity:
        activity = Activity(
            organization_id=organization_id,
            lead_id=lead_id,
            company_id=company_id,
            actor_id=actor_id,
            activity_type=activity_type,
            summary=summary,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def list_for_lead(
        self, lead_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[Activity], int]:
        total = await self.db.scalar(
            select(func.count(Activity.id)).where(Activity.lead_id == lead_id)
        ) or 0
        result = await self.db.scalars(
            select(Activity)
            .options(selectinload(Activity.actor))
            .where(Activity.lead_id == lead_id)
            .order_by(Activity.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total

    async def list_for_company(
        self, company_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[Activity], int]:
        total = await self.db.scalar(
            select(func.count(Activity.id)).where(Activity.company_id == company_id)
        ) or 0
        result = await self.db.scalars(
            select(Activity)
            .options(selectinload(Activity.actor))
            .where(Activity.company_id == company_id)
            .order_by(Activity.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total
