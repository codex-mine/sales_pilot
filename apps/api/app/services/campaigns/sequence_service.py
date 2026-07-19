"""
Campaigns -> Sequence + SequenceStep CRUD.

`SequenceStep` has no dedicated "content_source" column (V1 reuses the
existing schema only, no migration) — the AI-personalized-vs-template choice
is stored as an explicit sibling key inside the existing `condition` JSONB
(`{"content_source": "template" | "ai_personalized", "skip_if": ...}`), never
inferred from whether `email_template_id` happens to be set. This service is
the only place that packs/unpacks that key; callers (routes, serializers,
the scheduler) always see `content_source` as its own explicit field.
"""

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.campaigns.models import Sequence, SequenceStep
from app.models.enums import AuditActionEnum, SequenceStepTypeEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.email_template_repository import EmailTemplateRepository
from app.repositories.sequence_repository import SequenceRepository
from app.schemas.campaigns import (
    SequenceCreateRequest,
    SequenceStepCreateRequest,
    SequenceStepUpdateRequest,
    SequenceUpdateRequest,
)

_DEFAULT_CONTENT_SOURCE = "template"


def split_condition(condition: dict | None) -> tuple[dict, str]:
    """(branching_rules, content_source) — the response-serializer counterpart
    to this module's packing logic."""
    condition = dict(condition or {})
    content_source = condition.pop("content_source", _DEFAULT_CONTENT_SOURCE)
    return condition, content_source


class SequenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.sequences = SequenceRepository(db)
        self.templates = EmailTemplateRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_sequence(self, sequence_id: uuid.UUID, organization_id: uuid.UUID) -> Sequence:
        sequence = await self.sequences.get_by_id(sequence_id, organization_id)
        if sequence is None:
            raise NotFoundError("Sequence not found.")
        return sequence

    async def require_step(self, step_id: uuid.UUID, organization_id: uuid.UUID) -> SequenceStep:
        step = await self.sequences.get_step_by_id(step_id, organization_id)
        if step is None:
            raise NotFoundError("Sequence step not found.")
        return step

    # ─── Sequence ───────────────────────────────────────────────────────────────

    async def list_for_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> list[Sequence]:
        await self._require_campaign(campaign_id, organization_id)
        return await self.sequences.list_for_campaign(campaign_id, organization_id)

    async def create_sequence(
        self, campaign_id: uuid.UUID, organization_id: uuid.UUID, *, payload: SequenceCreateRequest, actor: User
    ) -> Sequence:
        await self._require_campaign(campaign_id, organization_id)
        sequence = await self.sequences.create(
            campaign_id=campaign_id, organization_id=organization_id, **payload.model_dump()
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="sequence", resource_id=sequence.id,
            changes={"event": "sequence_created", "campaign_id": str(campaign_id), "name": sequence.name},
        )
        await self.db.commit()
        return await self.require_sequence(sequence.id, organization_id)

    async def update_sequence(self, sequence: Sequence, *, payload: SequenceUpdateRequest, actor: User) -> Sequence:
        changes = payload.model_dump(exclude_unset=True)
        sequence = await self.sequences.update(sequence, changes)
        await self.audit_log.record(
            organization_id=sequence.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="sequence", resource_id=sequence.id,
            changes={"event": "sequence_updated", "fields": sorted(changes)},
        )
        await self.db.commit()
        return await self.require_sequence(sequence.id, sequence.organization_id)

    async def _require_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        campaign = await self.campaigns.get_by_id(campaign_id, organization_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

    # ─── Steps ──────────────────────────────────────────────────────────────────

    async def _validate_content(
        self, organization_id: uuid.UUID, *, step_type: str, content_source: str, email_template_id: uuid.UUID | None
    ) -> None:
        if step_type != SequenceStepTypeEnum.EMAIL.value:
            return
        if content_source == "template":
            if email_template_id is None:
                raise ValidationError(
                    "A template-based step requires email_template_id.",
                    errors={"email_template_id": ["Required when content_source is 'template'."]},
                )
            template = await self.templates.get_by_id(email_template_id, organization_id)
            if template is None:
                raise NotFoundError("Email template not found.")
        elif email_template_id is not None:
            raise ValidationError(
                "An AI-personalized step must not reference a fixed template.",
                errors={"email_template_id": ["Must be empty when content_source is 'ai_personalized'."]},
            )

    async def create_step(
        self, sequence_id: uuid.UUID, organization_id: uuid.UUID, *, payload: SequenceStepCreateRequest, actor: User
    ) -> SequenceStep:
        sequence = await self.require_sequence(sequence_id, organization_id)
        await self._validate_content(
            organization_id, step_type=payload.step_type, content_source=payload.content_source,
            email_template_id=payload.email_template_id,
        )
        fields: dict[str, Any] = payload.model_dump(exclude={"condition", "content_source"})
        fields["condition"] = {**(payload.condition or {}), "content_source": payload.content_source}

        step = await self.sequences.create_step(sequence_id=sequence.id, organization_id=organization_id, **fields)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="sequence_step", resource_id=step.id,
            changes={"event": "sequence_step_added", "sequence_id": str(sequence_id), "step_type": payload.step_type},
        )
        await self.db.commit()
        return await self.require_step(step.id, organization_id)

    async def update_step(
        self, step: SequenceStep, *, payload: SequenceStepUpdateRequest, actor: User
    ) -> SequenceStep:
        set_fields = payload.model_fields_set
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True, exclude={"condition", "content_source"})

        if "condition" in set_fields or "content_source" in set_fields:
            existing_rules, existing_source = split_condition(step.condition)
            new_rules = payload.condition if "condition" in set_fields else existing_rules
            new_source = payload.content_source if "content_source" in set_fields else existing_source
            resolved_template_id = (
                changes.get("email_template_id") if "email_template_id" in set_fields else step.email_template_id
            )
            await self._validate_content(
                step.organization_id, step_type=step.step_type, content_source=new_source,
                email_template_id=resolved_template_id,
            )
            changes["condition"] = {**(new_rules or {}), "content_source": new_source}
        elif "email_template_id" in set_fields:
            _rules, existing_source = split_condition(step.condition)
            await self._validate_content(
                step.organization_id, step_type=step.step_type, content_source=existing_source,
                email_template_id=changes["email_template_id"],
            )

        step = await self.sequences.update_step(step, changes)
        await self.audit_log.record(
            organization_id=step.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="sequence_step", resource_id=step.id,
            changes={"event": "sequence_step_updated", "fields": sorted(changes)},
        )
        await self.db.commit()
        return await self.require_step(step.id, step.organization_id)

    async def delete_step(self, step: SequenceStep, *, actor: User) -> None:
        await self.audit_log.record(
            organization_id=step.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="sequence_step", resource_id=step.id,
            changes={"event": "sequence_step_deleted", "sequence_id": str(step.sequence_id)},
        )
        await self.sequences.delete_step(step)
        await self.db.commit()

    async def move_step(self, step: SequenceStep, *, direction: Literal["up", "down"], actor: User) -> list[SequenceStep]:
        siblings = sorted(await self.sequences.list_steps(step.sequence_id, step.organization_id), key=lambda s: s.step_order)
        index = next(i for i, s in enumerate(siblings) if s.id == step.id)
        swap_index = index - 1 if direction == "up" else index + 1
        if swap_index < 0 or swap_index >= len(siblings):
            return siblings  # already at the boundary — no-op

        other = siblings[swap_index]
        this_order, other_order = step.step_order, other.step_order
        # A temporary sentinel avoids a transient unique-constraint collision
        # while both rows briefly share the "wrong" order mid-swap.
        await self.sequences.update_step(step, {"step_order": -1})
        await self.sequences.update_step(other, {"step_order": this_order})
        await self.sequences.update_step(step, {"step_order": other_order})
        await self.audit_log.record(
            organization_id=step.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="sequence_step", resource_id=step.id,
            changes={"event": "sequence_step_reordered", "direction": direction},
        )
        await self.db.commit()
        return await self.sequences.list_steps(step.sequence_id, step.organization_id)
