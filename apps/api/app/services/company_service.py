"""
Core Company CRUD, archive/restore, owner/tag management, bulk actions, logo
upload, and CSV export (CRM -> Companies).

Notes/Attachments/Timeline reuse NoteService/AttachmentService/
ActivityRepository (shared with Leads — see those modules' docstrings for
why). Employees is a read-only view over Contact, served directly off
CompanyRepository.list_employees — no employee-management logic lives here,
per the module's explicit scope (deferred to a future Contacts module).
"""

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.crm.models import Company
from app.models.enums import ActivityTypeEnum, AuditActionEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.user_repository import UserRepository
from app.schemas.companies import BulkCompanyActionRequest, CompanyCreateRequest, CompanyUpdateRequest
from app.services.storage_service import StorageService


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


def _normalize_domain(website: str | None) -> str | None:
    """Best-effort hostname extraction for the `uq_company_org_domain` dedup
    constraint — e.g. 'https://www.acme.com/about' -> 'acme.com'. Returns
    None (constraint allows multiple NULLs) if no usable hostname exists."""
    if not website:
        return None
    candidate = website if "//" in website else f"//{website}"
    host = urlparse(candidate).hostname
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


class CompanyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.companies = CompanyRepository(db)
        self.tags = TagRepository(db)
        self.users = UserRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.storage = StorageService()

    async def _validate_owner(self, organization_id: uuid.UUID, owner_id: uuid.UUID | None) -> None:
        if owner_id is None:
            return
        owner = await self.users.get_by_id(owner_id)
        if owner is None or owner.organization_id != organization_id:
            raise ValidationError(
                "Owner must be a member of this organization.", errors={"owner_id": ["Invalid owner."]}
            )

    async def create(self, *, organization_id: uuid.UUID, payload: CompanyCreateRequest, actor: User) -> Company:
        await self._validate_owner(organization_id, payload.owner_id)

        fields: dict[str, Any] = payload.model_dump(exclude={"tags", "address"})
        if payload.address is not None:
            fields["address"] = {k: v for k, v in payload.address.model_dump().items() if v is not None}
        fields["domain"] = _normalize_domain(payload.website)

        if fields["domain"]:
            existing = await self.companies.get_by_domain(organization_id, fields["domain"])
            if existing is not None:
                raise ValidationError(
                    "A company with this website already exists.",
                    errors={"website": ["Already in use."]},
                )

        company = await self.companies.create(organization_id=organization_id, created_by=actor.id, **fields)

        if payload.tags:
            tag_rows = await self.tags.get_or_create_many(organization_id, payload.tags)
            await self.tags.set_tags_for_company(company, tag_rows)

        await self.activities.record(
            organization_id=organization_id, company_id=company.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.COMPANY_CREATED,
            summary=f"Company created by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="company", resource_id=company.id,
        )
        await self.db.commit()
        return await self.companies.get_by_id(company.id, organization_id)  # type: ignore[return-value]

    async def update(self, company: Company, *, payload: CompanyUpdateRequest, actor: User) -> Company:
        changes = payload.model_dump(exclude={"tags", "address"}, exclude_unset=True)
        if "address" in payload.model_fields_set and payload.address is not None:
            changes["address"] = {k: v for k, v in payload.address.model_dump().items() if v is not None}

        if "owner_id" in changes:
            await self._validate_owner(company.organization_id, changes["owner_id"])

        if "website" in changes:
            new_domain = _normalize_domain(changes["website"])
            if new_domain and new_domain != company.domain:
                existing = await self.companies.get_by_domain(company.organization_id, new_domain)
                if existing is not None and existing.id != company.id:
                    raise ValidationError(
                        "A company with this website already exists.",
                        errors={"website": ["Already in use."]},
                    )
            changes["domain"] = new_domain

        before = {field: getattr(company, field) for field in changes}
        company = await self.companies.update(company, changes, updated_by=actor.id)

        await self._log_field_changes(company, before, changes, actor)

        if payload.tags is not None:
            tag_rows = await self.tags.get_or_create_many(company.organization_id, payload.tags)
            await self.tags.set_tags_for_company(company, tag_rows)
            await self.activities.record(
                organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.TAGS_CHANGED,
                summary=f"Tags updated by {actor.full_name}",
            )

        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="company", resource_id=company.id,
            changes={"before": _json_safe(before), "after": _json_safe(changes)},
        )
        await self.db.commit()
        return await self.companies.get_by_id(company.id, company.organization_id)  # type: ignore[return-value]

    async def _log_field_changes(
        self, company: Company, before: dict[str, Any], changes: dict[str, Any], actor: User
    ) -> None:
        if "status" in changes and before["status"] != changes["status"]:
            await self.activities.record(
                organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.STATUS_CHANGED,
                summary=f"Status changed from {before['status']} to {changes['status']}",
            )
        if "owner_id" in changes and before["owner_id"] != changes["owner_id"]:
            await self.activities.record(
                organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.OWNER_CHANGED,
                summary=f"Owner changed by {actor.full_name}",
            )
        other_fields = set(changes) - {"status", "owner_id", "domain"}
        if other_fields:
            await self.activities.record(
                organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.COMPANY_UPDATED,
                summary=f"Company updated by {actor.full_name}",
                metadata={"fields": sorted(other_fields)},
            )

    async def archive(self, company: Company, *, actor: User) -> Company:
        return await self._set_archived(company, True, actor)

    async def restore(self, company: Company, *, actor: User) -> Company:
        return await self._set_archived(company, False, actor)

    async def _set_archived(self, company: Company, archived: bool, actor: User) -> Company:
        company = await self.companies.update(
            company, {"archived_at": datetime.now(timezone.utc) if archived else None}, updated_by=actor.id
        )
        await self.activities.record(
            organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.COMPANY_ARCHIVED if archived else ActivityTypeEnum.COMPANY_RESTORED,
            summary=f"{'Archived' if archived else 'Restored'} by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="company", resource_id=company.id,
            changes={"archived": archived},
        )
        await self.db.commit()
        return await self.companies.get_by_id(company.id, company.organization_id)  # type: ignore[return-value]

    async def delete(self, company: Company, *, actor: User) -> None:
        await self.companies.soft_delete(company)
        await self.activities.record(
            organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.COMPANY_DELETED,
            summary=f"Company deleted by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="company", resource_id=company.id,
        )
        await self.db.commit()

    # ─── Logo ───────────────────────────────────────────────────────────────────

    async def upload_logo(self, company: Company, *, file: UploadFile, actor: User) -> Company:
        logo_url = await self.storage.save_company_logo(company.organization_id, company.id, file)
        company = await self.companies.update(company, {"logo_url": logo_url}, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="company", resource_id=company.id,
            changes={"logo_url": logo_url},
        )
        await self.db.commit()
        return await self.companies.get_by_id(company.id, company.organization_id)  # type: ignore[return-value]

    async def delete_logo(self, company: Company, *, actor: User) -> Company:
        self.storage.delete_company_logo(company.organization_id, company.id)
        company = await self.companies.update(company, {"logo_url": None}, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="company", resource_id=company.id,
            changes={"logo_url": None},
        )
        await self.db.commit()
        return await self.companies.get_by_id(company.id, company.organization_id)  # type: ignore[return-value]

    # ─── Bulk actions ───────────────────────────────────────────────────────────

    async def bulk_action(
        self, *, organization_id: uuid.UUID, payload: BulkCompanyActionRequest, actor: User
    ) -> tuple[int, int, list[tuple[uuid.UUID, str]]]:
        companies = await self.companies.get_many_by_ids(payload.company_ids, organization_id)
        found_ids = {company.id for company in companies}
        errors: list[tuple[uuid.UUID, str]] = [
            (cid, "Company not found in this organization.")
            for cid in payload.company_ids
            if cid not in found_ids
        ]

        if payload.action == "assign_owner":
            await self._validate_owner(organization_id, payload.owner_id)
        if payload.action in ("add_tags", "remove_tags") and not payload.tags:
            raise ValidationError("Provide at least one tag.", errors={"tags": ["Required."]})

        success_ids: list[uuid.UUID] = []
        for company in companies:
            try:
                await self._apply_bulk_action_to_company(company, payload, actor)
                success_ids.append(company.id)
            except (ValidationError, NotFoundError) as exc:
                errors.append((company.id, str(exc)))

        if payload.action in ("add_tags", "remove_tags") and success_ids:
            tag_rows = await self.tags.get_or_create_many(organization_id, payload.tags or [])
            if payload.action == "add_tags":
                await self.tags.add_tags_to_companies(success_ids, tag_rows)
            else:
                await self.tags.remove_tags_from_companies(success_ids, [t.id for t in tag_rows])

        for company_id in success_ids:
            await self.activities.record(
                organization_id=organization_id, company_id=company_id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.BULK_ACTION,
                summary=f"Bulk '{payload.action}' applied by {actor.full_name}",
            )

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE if payload.action != "delete" else AuditActionEnum.DELETE,
            resource_type="company", resource_id=None,
            changes={"bulk_action": payload.action, "company_ids": [str(i) for i in success_ids]},
        )
        await self.db.commit()
        return len(payload.company_ids), len(success_ids), errors

    async def _apply_bulk_action_to_company(
        self, company: Company, payload: BulkCompanyActionRequest, actor: User
    ) -> None:
        if payload.action == "delete":
            await self.companies.soft_delete(company)
        elif payload.action == "archive":
            await self.companies.update(company, {"archived_at": datetime.now(timezone.utc)}, updated_by=actor.id)
        elif payload.action == "restore":
            await self.companies.update(company, {"archived_at": None}, updated_by=actor.id)
        elif payload.action == "assign_owner":
            await self.companies.update(company, {"owner_id": payload.owner_id}, updated_by=actor.id)
        elif payload.action == "change_status":
            if not payload.status:
                raise ValidationError("Status is required.", errors={"status": ["Required."]})
            await self.companies.update(company, {"status": payload.status}, updated_by=actor.id)
        # add_tags / remove_tags are applied in bulk after the loop (see bulk_action)

    async def get_counts(self, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        return await self.companies.counts_for_companies(company_ids)

    async def require_company(self, company_id: uuid.UUID, organization_id: uuid.UUID) -> Company:
        company = await self.companies.get_by_id(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company not found.")
        return company

    # ─── CSV export ─────────────────────────────────────────────────────────────

    async def export_csv(self, *, companies: list[Company]) -> str:
        buffer = io.StringIO()
        columns = [
            "name", "legal_name", "website", "industry", "phone", "email", "founded_year",
            "size_range", "employee_count", "annual_revenue", "currency", "country", "state",
            "city", "postal_code", "linkedin_url", "twitter_url", "status", "tags",
            "owner_email", "created_at", "updated_at",
        ]
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for company in companies:
            writer.writerow(
                {
                    "name": company.name,
                    "legal_name": company.legal_name or "",
                    "website": company.website or "",
                    "industry": company.industry or "",
                    "phone": company.phone or "",
                    "email": company.email or "",
                    "founded_year": company.founded_year or "",
                    "size_range": company.size_range or "",
                    "employee_count": company.employee_count if company.employee_count is not None else "",
                    "annual_revenue": company.annual_revenue if company.annual_revenue is not None else "",
                    "currency": company.currency,
                    "country": company.country or "",
                    "state": company.state or "",
                    "city": company.city or "",
                    "postal_code": company.postal_code or "",
                    "linkedin_url": company.linkedin_url or "",
                    "twitter_url": company.twitter_url or "",
                    "status": company.status,
                    "tags": ", ".join(tag.name for tag in company.tags),
                    "owner_email": company.owner.email if company.owner else "",
                    "created_at": company.created_at.isoformat(),
                    "updated_at": company.updated_at.isoformat(),
                }
            )
        return buffer.getvalue()
