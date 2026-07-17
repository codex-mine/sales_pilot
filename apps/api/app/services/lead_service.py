"""
Core Lead CRUD, favorite/archive/restore, and bulk actions.

CSV import/export lives in `lead_import_export_service.py` (shares little
logic with plain CRUD and is substantial enough to stay isolated). Notes and
attachments live in their own services for the same reason.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.crm.models import Lead
from app.models.enums import AuditActionEnum, ActivityTypeEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.user_repository import UserRepository
from app.schemas.leads import BulkLeadActionRequest, LeadCreateRequest, LeadUpdateRequest


def _json_safe(value: Any) -> Any:
    """Audit log `changes` is stored as JSONB — UUIDs (e.g. owner_id) aren't
    natively JSON-serializable, so stringify anything that isn't already a
    plain JSON-compatible type before it reaches the DB driver."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


class LeadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.tags = TagRepository(db)
        self.users = UserRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def _validate_owner(self, organization_id: uuid.UUID, owner_id: uuid.UUID | None) -> None:
        if owner_id is None:
            return
        owner = await self.users.get_by_id(owner_id)
        if owner is None or owner.organization_id != organization_id:
            raise ValidationError(
                "Owner must be a member of this organization.", errors={"owner_id": ["Invalid owner."]}
            )

    async def create(self, *, organization_id: uuid.UUID, payload: LeadCreateRequest, actor: User) -> Lead:
        if not any([payload.first_name, payload.last_name, payload.email, payload.company_name]):
            raise ValidationError(
                "A lead needs at least a name, email, or company.",
                errors={"first_name": ["Provide a name, email, or company."]},
            )
        await self._validate_owner(organization_id, payload.owner_id)

        fields: dict[str, Any] = payload.model_dump(exclude={"tags", "address"})
        if payload.address is not None:
            fields["address"] = {k: v for k, v in payload.address.model_dump().items() if v is not None}

        lead = await self.leads.create(organization_id=organization_id, created_by=actor.id, **fields)

        if payload.tags:
            tag_rows = await self.tags.get_or_create_many(organization_id, payload.tags)
            await self.tags.set_tags_for_lead(lead, tag_rows)

        await self.activities.record(
            organization_id=organization_id, lead_id=lead.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.LEAD_CREATED,
            summary=f"Lead created by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="lead", resource_id=lead.id,
        )
        await self.db.commit()
        await self.db.refresh(lead)
        return await self.leads.get_by_id(lead.id, organization_id)  # type: ignore[return-value]

    async def update(self, lead: Lead, *, payload: LeadUpdateRequest, actor: User) -> Lead:
        changes = payload.model_dump(exclude={"tags", "address"}, exclude_unset=True)
        if "address" in payload.model_fields_set and payload.address is not None:
            changes["address"] = {k: v for k, v in payload.address.model_dump().items() if v is not None}

        if "owner_id" in changes:
            await self._validate_owner(lead.organization_id, changes["owner_id"])

        before = {field: getattr(lead, field) for field in changes}
        lead = await self.leads.update(lead, changes, updated_by=actor.id)

        await self._log_field_changes(lead, before, changes, actor)

        if payload.tags is not None:
            tag_rows = await self.tags.get_or_create_many(lead.organization_id, payload.tags)
            await self.tags.set_tags_for_lead(lead, tag_rows)
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.TAGS_CHANGED,
                summary=f"Tags updated by {actor.full_name}",
            )

        await self.audit_log.record(
            organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="lead", resource_id=lead.id,
            changes={"before": _json_safe(before), "after": _json_safe(changes)},
        )
        await self.db.commit()
        return await self.leads.get_by_id(lead.id, lead.organization_id)  # type: ignore[return-value]

    async def _log_field_changes(
        self, lead: Lead, before: dict[str, Any], changes: dict[str, Any], actor: User
    ) -> None:
        if "status" in changes and before["status"] != changes["status"]:
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.STATUS_CHANGED,
                summary=f"Status changed from {before['status']} to {changes['status']}",
            )
        if "owner_id" in changes and before["owner_id"] != changes["owner_id"]:
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.OWNER_CHANGED,
                summary=f"Owner changed by {actor.full_name}",
            )
        if "is_favorite" in changes and before["is_favorite"] != changes["is_favorite"]:
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=(
                    ActivityTypeEnum.LEAD_FAVORITED if changes["is_favorite"] else ActivityTypeEnum.LEAD_UNFAVORITED
                ),
                summary=f"{'Favorited' if changes['is_favorite'] else 'Unfavorited'} by {actor.full_name}",
            )
        if "is_archived" in changes and before["is_archived"] != changes["is_archived"]:
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=(
                    ActivityTypeEnum.LEAD_ARCHIVED if changes["is_archived"] else ActivityTypeEnum.LEAD_RESTORED
                ),
                summary=f"{'Archived' if changes['is_archived'] else 'Restored'} by {actor.full_name}",
            )
        other_fields = set(changes) - {"status", "owner_id", "is_favorite", "is_archived"}
        if other_fields:
            await self.activities.record(
                organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.LEAD_UPDATED,
                summary=f"Lead updated by {actor.full_name}",
                metadata={"fields": sorted(other_fields)},
            )

    async def delete(self, lead: Lead, *, actor: User) -> None:
        await self.leads.soft_delete(lead)
        await self.activities.record(
            organization_id=lead.organization_id, lead_id=lead.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.LEAD_DELETED,
            summary=f"Lead deleted by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=lead.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="lead", resource_id=lead.id,
        )
        await self.db.commit()

    # ─── Bulk actions ───────────────────────────────────────────────────────────

    async def bulk_action(
        self, *, organization_id: uuid.UUID, payload: BulkLeadActionRequest, actor: User
    ) -> tuple[int, int, list[tuple[uuid.UUID, str]]]:
        leads = await self.leads.get_many_by_ids(payload.lead_ids, organization_id)
        found_ids = {lead.id for lead in leads}
        errors: list[tuple[uuid.UUID, str]] = [
            (lid, "Lead not found in this organization.")
            for lid in payload.lead_ids
            if lid not in found_ids
        ]

        if payload.action == "assign_owner":
            await self._validate_owner(organization_id, payload.owner_id)
        if payload.action == "add_tags" or payload.action == "remove_tags":
            if not payload.tags:
                raise ValidationError("Provide at least one tag.", errors={"tags": ["Required."]})

        success_ids: list[uuid.UUID] = []
        for lead in leads:
            try:
                await self._apply_bulk_action_to_lead(lead, payload, actor)
                success_ids.append(lead.id)
            except (ValidationError, NotFoundError) as exc:
                # Per-row isolation: one bad row doesn't fail the whole batch.
                errors.append((lead.id, str(exc)))

        if payload.action in ("add_tags", "remove_tags") and success_ids:
            tag_rows = await self.tags.get_or_create_many(organization_id, payload.tags or [])
            if payload.action == "add_tags":
                await self.tags.add_tags_to_leads(success_ids, tag_rows)
            else:
                await self.tags.remove_tags_from_leads(success_ids, [t.id for t in tag_rows])

        for lead_id in success_ids:
            await self.activities.record(
                organization_id=organization_id, lead_id=lead_id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.BULK_ACTION,
                summary=f"Bulk '{payload.action}' applied by {actor.full_name}",
            )

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE if payload.action != "delete" else AuditActionEnum.DELETE,
            resource_type="lead", resource_id=None,
            changes={"bulk_action": payload.action, "lead_ids": [str(i) for i in success_ids]},
        )
        await self.db.commit()
        return len(payload.lead_ids), len(success_ids), errors

    async def _apply_bulk_action_to_lead(
        self, lead: Lead, payload: BulkLeadActionRequest, actor: User
    ) -> None:
        if payload.action == "delete":
            await self.leads.soft_delete(lead)
        elif payload.action == "archive":
            await self.leads.update(lead, {"is_archived": True}, updated_by=actor.id)
        elif payload.action == "restore":
            await self.leads.update(lead, {"is_archived": False}, updated_by=actor.id)
        elif payload.action == "favorite":
            await self.leads.update(lead, {"is_favorite": True}, updated_by=actor.id)
        elif payload.action == "unfavorite":
            await self.leads.update(lead, {"is_favorite": False}, updated_by=actor.id)
        elif payload.action == "assign_owner":
            await self.leads.update(lead, {"owner_id": payload.owner_id}, updated_by=actor.id)
        elif payload.action == "change_status":
            if not payload.status:
                raise ValidationError("Status is required.", errors={"status": ["Required."]})
            await self.leads.update(lead, {"status": payload.status}, updated_by=actor.id)
        # add_tags / remove_tags are applied in bulk after the loop (see bulk_action)

    async def get_counts(self, lead_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        return await self.leads.counts_for_leads(lead_ids)

    async def require_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> Lead:
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        return lead
