import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaigns.models import Campaign, CampaignLead, SequenceStep
from app.models.enums import CampaignLeadStatusEnum

_DUE_STATUSES = (CampaignLeadStatusEnum.ENROLLED.value, CampaignLeadStatusEnum.IN_PROGRESS.value)


class CampaignLeadRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, campaign_lead_id: uuid.UUID, organization_id: uuid.UUID) -> CampaignLead | None:
        return await self.db.scalar(
            select(CampaignLead)
            .options(
                selectinload(CampaignLead.lead),
                selectinload(CampaignLead.campaign),
                selectinload(CampaignLead.next_step),
            )
            .where(CampaignLead.id == campaign_lead_id, CampaignLead.organization_id == organization_id)
        )

    async def get_for_processing(self, campaign_lead_id: uuid.UUID) -> CampaignLead | None:
        """Unscoped by organization (the worker task only has the id, not an
        authenticated caller's org) and locked, mirroring `EmailRepository.
        get_for_update`'s reasoning for the same kind of background task.

        `populate_existing()` is required here: `advance_after_send` re-locks
        a row that `execute_step` may have already loaded earlier in the same
        session (e.g. the scheduler's own full-automation send path calls
        both within one `execute_step` invocation). Without it, SQLAlchemy's
        identity map returns the already-cached object as-is — including a
        stale `next_step` relationship pointing at the step that was just
        completed, even though `next_step_id` was already advanced — instead
        of reflecting the update this same call just committed."""
        return await self.db.scalar(
            select(CampaignLead)
            .options(
                selectinload(CampaignLead.lead),
                selectinload(CampaignLead.campaign).selectinload(Campaign.owner),
                selectinload(CampaignLead.next_step).selectinload(SequenceStep.email_template),
            )
            .where(CampaignLead.id == campaign_lead_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def get_by_campaign_and_lead(self, campaign_id: uuid.UUID, lead_id: uuid.UUID) -> CampaignLead | None:
        return await self.db.scalar(
            select(CampaignLead).where(CampaignLead.campaign_id == campaign_id, CampaignLead.lead_id == lead_id)
        )

    async def list_for_campaign(
        self,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        status: list[str] | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[CampaignLead], int]:
        conditions = [CampaignLead.campaign_id == campaign_id, CampaignLead.organization_id == organization_id]
        if status:
            conditions.append(CampaignLead.status.in_(status))
        base = select(CampaignLead).where(and_(*conditions))
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.options(
                selectinload(CampaignLead.lead), selectinload(CampaignLead.campaign), selectinload(CampaignLead.next_step)
            )
            .order_by(CampaignLead.enrolled_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total

    async def list_for_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> list[CampaignLead]:
        result = await self.db.scalars(
            select(CampaignLead)
            .options(selectinload(CampaignLead.campaign), selectinload(CampaignLead.next_step))
            .where(CampaignLead.lead_id == lead_id, CampaignLead.organization_id == organization_id)
            .order_by(CampaignLead.enrolled_at.desc())
        )
        return list(result)

    async def create(self, *, campaign_id: uuid.UUID, lead_id: uuid.UUID, organization_id: uuid.UUID, **fields: Any) -> CampaignLead:
        campaign_lead = CampaignLead(campaign_id=campaign_id, lead_id=lead_id, organization_id=organization_id, **fields)
        self.db.add(campaign_lead)
        await self.db.flush()
        return campaign_lead

    async def update(self, campaign_lead: CampaignLead, changes: dict[str, Any]) -> CampaignLead:
        for field, value in changes.items():
            setattr(campaign_lead, field, value)
        await self.db.flush()
        return campaign_lead

    # ─── Scheduler ──────────────────────────────────────────────────────────────

    async def claim_due_batch(self, *, now: datetime, batch_size: int) -> list[uuid.UUID]:
        """`SELECT ... FOR UPDATE SKIP LOCKED` the due rows, then immediately
        clear `next_action_at` on those SAME rows within the same
        transaction, before the caller commits. This is what makes the claim
        atomic across concurrent scheduler passes: once this transaction
        commits, the rows are no longer "due" (next_action_at is NULL) even
        though `execute_campaign_step` hasn't actually processed them yet —
        without this, a second scheduler pass starting immediately after this
        one commits would see the same still-due rows and double-dispatch
        them. See `models/ARCHITECTURE.md` §3."""
        result = await self.db.execute(
            select(CampaignLead.id)
            .where(
                CampaignLead.next_action_at.is_not(None),
                CampaignLead.next_action_at <= now,
                CampaignLead.status.in_(_DUE_STATUSES),
            )
            .order_by(CampaignLead.next_action_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        ids = [row[0] for row in result.all()]
        if ids:
            await self.db.execute(update(CampaignLead).where(CampaignLead.id.in_(ids)).values(next_action_at=None))
        return ids

    async def funnel_counts_for_campaigns(self, campaign_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        if not campaign_ids:
            return {}
        result: dict[uuid.UUID, dict[str, int]] = {cid: {} for cid in campaign_ids}
        rows = await self.db.execute(
            select(CampaignLead.campaign_id, CampaignLead.status, func.count(CampaignLead.id))
            .where(CampaignLead.campaign_id.in_(campaign_ids))
            .group_by(CampaignLead.campaign_id, CampaignLead.status)
        )
        for campaign_id, status, count in rows.all():
            result[campaign_id][status] = count
        return result
