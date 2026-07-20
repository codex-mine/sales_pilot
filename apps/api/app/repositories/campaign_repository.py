import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaigns.models import Campaign, CampaignLead


class CampaignRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> Campaign | None:
        return await self.db.scalar(
            select(Campaign)
            .options(selectinload(Campaign.owner))
            .where(
                Campaign.id == campaign_id, Campaign.organization_id == organization_id,
                Campaign.deleted_at.is_(None),
            )
        )

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Campaign], int]:
        conditions = [Campaign.organization_id == organization_id, Campaign.deleted_at.is_(None)]
        if status:
            conditions.append(Campaign.status.in_(status))
        if search:
            conditions.append(func.lower(Campaign.name).like(f"%{search.strip().lower()}%"))

        base = select(Campaign).where(and_(*conditions))
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.options(selectinload(Campaign.owner))
            .order_by(Campaign.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> Campaign:
        campaign = Campaign(organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields)
        self.db.add(campaign)
        await self.db.flush()
        return campaign

    async def update(self, campaign: Campaign, changes: dict[str, Any], *, updated_by: uuid.UUID | None) -> Campaign:
        for field, value in changes.items():
            setattr(campaign, field, value)
        campaign.updated_by = updated_by
        await self.db.flush()
        return campaign

    async def soft_delete(self, campaign: Campaign) -> None:
        from datetime import datetime, timezone

        campaign.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def enrolled_count(self, campaign_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(CampaignLead.id)).where(CampaignLead.campaign_id == campaign_id)
        ) or 0

    async def funnel_counts(self, campaign_id: uuid.UUID) -> dict[str, int]:
        rows = await self.db.execute(
            select(CampaignLead.status, func.count(CampaignLead.id))
            .where(CampaignLead.campaign_id == campaign_id)
            .group_by(CampaignLead.status)
        )
        return {status: count for status, count in rows.all()}

    async def enrolled_counts_for_campaigns(self, campaign_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not campaign_ids:
            return {}
        rows = await self.db.execute(
            select(CampaignLead.campaign_id, func.count(CampaignLead.id))
            .where(CampaignLead.campaign_id.in_(campaign_ids))
            .group_by(CampaignLead.campaign_id)
        )
        return dict(rows.all())
