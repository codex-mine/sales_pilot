import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.campaigns.models import Sequence, SequenceStep


class SequenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, sequence_id: uuid.UUID, organization_id: uuid.UUID) -> Sequence | None:
        return await self.db.scalar(
            select(Sequence)
            .options(selectinload(Sequence.steps).selectinload(SequenceStep.email_template))
            .where(Sequence.id == sequence_id, Sequence.organization_id == organization_id)
        )

    async def list_for_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> list[Sequence]:
        result = await self.db.scalars(
            select(Sequence)
            .options(selectinload(Sequence.steps).selectinload(SequenceStep.email_template))
            .where(Sequence.campaign_id == campaign_id, Sequence.organization_id == organization_id)
            .order_by(Sequence.created_at)
        )
        return list(result)

    async def get_first_active(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> Sequence | None:
        return await self.db.scalar(
            select(Sequence)
            .options(selectinload(Sequence.steps).selectinload(SequenceStep.email_template))
            .where(
                Sequence.campaign_id == campaign_id, Sequence.organization_id == organization_id,
                Sequence.is_active.is_(True),
            )
            .order_by(Sequence.created_at)
            .limit(1)
        )

    async def create(self, *, campaign_id: uuid.UUID, organization_id: uuid.UUID, **fields: Any) -> Sequence:
        sequence = Sequence(campaign_id=campaign_id, organization_id=organization_id, **fields)
        self.db.add(sequence)
        await self.db.flush()
        return sequence

    async def update(self, sequence: Sequence, changes: dict[str, Any]) -> Sequence:
        for field, value in changes.items():
            setattr(sequence, field, value)
        await self.db.flush()
        return sequence

    # ─── Steps ──────────────────────────────────────────────────────────────────

    async def get_step_by_id(self, step_id: uuid.UUID, organization_id: uuid.UUID) -> SequenceStep | None:
        return await self.db.scalar(
            select(SequenceStep)
            .options(selectinload(SequenceStep.email_template))
            .where(SequenceStep.id == step_id, SequenceStep.organization_id == organization_id)
        )

    async def list_steps(self, sequence_id: uuid.UUID, organization_id: uuid.UUID) -> list[SequenceStep]:
        result = await self.db.scalars(
            select(SequenceStep)
            .options(selectinload(SequenceStep.email_template))
            .where(SequenceStep.sequence_id == sequence_id, SequenceStep.organization_id == organization_id)
            .order_by(SequenceStep.step_order)
        )
        return list(result)

    async def get_next_step(self, sequence_id: uuid.UUID, after_step_order: int) -> SequenceStep | None:
        """The next active step strictly after `after_step_order`, by
        ascending order — used by the scheduler to advance a CampaignLead."""
        return await self.db.scalar(
            select(SequenceStep)
            .where(
                SequenceStep.sequence_id == sequence_id, SequenceStep.step_order > after_step_order,
                SequenceStep.is_active.is_(True),
            )
            .order_by(SequenceStep.step_order)
            .limit(1)
        )

    async def create_step(self, *, sequence_id: uuid.UUID, organization_id: uuid.UUID, **fields: Any) -> SequenceStep:
        step = SequenceStep(sequence_id=sequence_id, organization_id=organization_id, **fields)
        self.db.add(step)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise _step_order_conflict() from exc
        return step

    async def update_step(self, step: SequenceStep, changes: dict[str, Any]) -> SequenceStep:
        for field, value in changes.items():
            setattr(step, field, value)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise _step_order_conflict() from exc
        return step

    async def delete_step(self, step: SequenceStep) -> None:
        await self.db.delete(step)
        await self.db.flush()


def _step_order_conflict():
    from app.exceptions.errors import ValidationError

    return ValidationError(
        "Another step in this sequence already uses that position.",
        errors={"step_order": ["Already in use within this sequence."]},
    )
