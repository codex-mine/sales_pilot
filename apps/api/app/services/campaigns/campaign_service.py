"""
Campaigns -> Campaign CRUD + status control. Follows `company_service.py`'s
exact pattern: Activity + AuditLog on every mutation, `_json_safe()` reuse,
soft delete via the existing `deleted_at` timestamp column.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import json_safe as _json_safe
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.campaigns.models import Campaign
from app.models.enums import AuditActionEnum, CampaignStatusEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.user_repository import UserRepository
from app.schemas.campaigns import CampaignCreateRequest, CampaignUpdateRequest
from app.services.campaigns.campaign_settings import pack_requires_approval

_ACTIVATE_FROM = {CampaignStatusEnum.DRAFT.value, CampaignStatusEnum.PAUSED.value}


class CampaignService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.users = UserRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> Campaign:
        campaign = await self.campaigns.get_by_id(campaign_id, organization_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign

    async def _validate_owner(self, organization_id: uuid.UUID, owner_id: uuid.UUID | None) -> None:
        if owner_id is None:
            return
        owner = await self.users.get_by_id(owner_id)
        if owner is None or owner.organization_id != organization_id:
            raise ValidationError(
                "Owner must be a member of this organization.", errors={"owner_id": ["Invalid owner."]}
            )

    async def create(self, *, organization_id: uuid.UUID, payload: CampaignCreateRequest, actor: User) -> Campaign:
        await self._validate_owner(organization_id, payload.owner_id)
        fields: dict[str, Any] = payload.model_dump(exclude={"requires_approval"})
        fields["settings"] = pack_requires_approval(None, payload.requires_approval)
        campaign = await self.campaigns.create(
            organization_id=organization_id, created_by=actor.id,
            status=CampaignStatusEnum.DRAFT.value, **fields,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_created", "name": campaign.name},
        )
        await self.db.commit()
        return await self.require_campaign(campaign.id, organization_id)

    async def update(self, campaign: Campaign, *, payload: CampaignUpdateRequest, actor: User) -> Campaign:
        changes = payload.model_dump(exclude_unset=True, exclude={"requires_approval"})
        if "owner_id" in changes:
            await self._validate_owner(campaign.organization_id, changes["owner_id"])
        if payload.requires_approval is not None:
            changes["settings"] = pack_requires_approval(campaign.settings, payload.requires_approval)

        before = {field: getattr(campaign, field) for field in changes}
        campaign = await self.campaigns.update(campaign, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=campaign.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_updated", "before": _json_safe(before), "after": _json_safe(changes)},
        )
        await self.db.commit()
        return await self.require_campaign(campaign.id, campaign.organization_id)

    async def delete(self, campaign: Campaign, *, actor: User) -> None:
        if campaign.status == CampaignStatusEnum.ACTIVE.value:
            raise ValidationError("Pause this campaign before deleting it.")
        await self.campaigns.soft_delete(campaign)
        await self.audit_log.record(
            organization_id=campaign.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_deleted"},
        )
        await self.db.commit()

    # ─── Status control ─────────────────────────────────────────────────────────

    async def activate(self, campaign: Campaign, *, actor: User) -> Campaign:
        if campaign.status not in _ACTIVATE_FROM:
            raise ValidationError(f"Cannot activate a campaign in '{campaign.status}' status.")
        from datetime import datetime, timezone

        changes: dict[str, Any] = {"status": CampaignStatusEnum.ACTIVE.value}
        if campaign.started_at is None:
            changes["started_at"] = datetime.now(timezone.utc)
        campaign = await self.campaigns.update(campaign, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=campaign.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_activated"},
        )
        await self.db.commit()
        return await self.require_campaign(campaign.id, campaign.organization_id)

    async def pause(self, campaign: Campaign, *, actor: User) -> Campaign:
        if campaign.status != CampaignStatusEnum.ACTIVE.value:
            raise ValidationError("Only an active campaign can be paused.")
        campaign = await self.campaigns.update(
            campaign, {"status": CampaignStatusEnum.PAUSED.value}, updated_by=actor.id
        )
        await self.audit_log.record(
            organization_id=campaign.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_paused"},
        )
        await self.db.commit()
        return await self.require_campaign(campaign.id, campaign.organization_id)

    async def archive(self, campaign: Campaign, *, actor: User) -> Campaign:
        if campaign.status == CampaignStatusEnum.ARCHIVED.value:
            raise ValidationError("This campaign is already archived.")
        campaign = await self.campaigns.update(
            campaign, {"status": CampaignStatusEnum.ARCHIVED.value}, updated_by=actor.id
        )
        await self.audit_log.record(
            organization_id=campaign.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="campaign", resource_id=campaign.id,
            changes={"event": "campaign_archived"},
        )
        await self.db.commit()
        return await self.require_campaign(campaign.id, campaign.organization_id)
