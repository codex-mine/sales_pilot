"""
Organization lifecycle: creation + system-role seeding.

Roles are org-scoped rows (ARCHITECTURE.md: "per-org RBAC" — enterprise
customers customize role names/permissions per tenant), so the six built-in
roles are (re)created for every new organization rather than shared globally.
Permission rows themselves *are* global (resource/action is an application
concept, not a tenant one) and are reused across organizations via
get_or_create.
"""

import uuid
from typing import Any, NoReturn

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import ConflictError
from app.models.enums import AuditActionEnum, RoleNameEnum
from app.models.identity.models import Organization, Role, User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.security.permissions import DEFAULT_ROLE_PERMISSIONS
from app.services.storage_service import StorageService


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.organizations = OrganizationRepository(db)
        self.roles = RoleRepository(db)
        self.users = UserRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.storage = StorageService()

    async def create_with_owner_role(self, name: str) -> tuple[Organization, Role]:
        slug = await self.organizations.generate_unique_slug(name)
        organization = await self.organizations.create(name=name, slug=slug)
        await self.seed_system_roles(organization.id)
        # Seed the AI system prompt templates alongside roles so AIJobService
        # never 404s on "no active prompt version" for a fresh organization.
        # (Deferred import: PromptService pulls in the AI schema module, and
        # organization_service is imported during auth flows that shouldn't
        # pay that import cost.)
        from app.services.ai.prompt_service import PromptService

        await PromptService(self.db).ensure_system_templates(organization.id)
        owner_role = await self.roles.get_by_name(
            organization.id, RoleNameEnum.OWNER.value
        )
        assert owner_role is not None
        return organization, owner_role

    async def seed_system_roles(self, organization_id: uuid.UUID) -> dict[str, Role]:
        created: dict[str, Role] = {}
        for role_name, grants in DEFAULT_ROLE_PERMISSIONS.items():
            role = await self.roles.create(
                organization_id=organization_id, name=role_name.value, is_system=True
            )
            permissions = [
                await self.roles.get_or_create_permission(resource, action)
                for resource, action in grants
            ]
            await self.roles.set_permissions(role, permissions)
            created[role_name.value] = role
        return created

    async def create_additional(self, *, actor: User, name: str) -> NoReturn:
        """
        `POST /organizations` for an already-authenticated user. The current
        schema gives every user exactly one organization (`User.organization_id`
        is a single FK — see the model's docstring), so there is nothing valid
        for this route to do; it always raises. Kept as a real, documented
        endpoint (not a 404) so API consumers get a clear, stable error instead
        of guessing why the "obvious" REST verb doesn't exist.
        """
        raise ConflictError(
            "This account already belongs to an organization. Creating additional "
            "organizations isn't supported yet — multi-organization membership is "
            "a planned future capability.",
        )

    async def update(
        self, organization: Organization, *, changes: dict[str, Any], actor: User
    ) -> Organization:
        if "slug" in changes and changes["slug"] != organization.slug:
            existing = await self.organizations.get_by_slug(changes["slug"])
            if existing is not None and existing.id != organization.id:
                raise ConflictError("This slug is already taken.")

        if "address" in changes and changes["address"] is not None:
            # `changes` comes from the route's `payload.model_dump(exclude_unset=True)`,
            # which already recursively dumps the nested `OrganizationAddress` model to
            # a plain dict — strip the Nones it leaves for fields the caller didn't set.
            changes["address"] = {k: v for k, v in changes["address"].items() if v is not None}

        before = {field: getattr(organization, field) for field in changes}
        organization = await self.organizations.update(organization, changes)
        await self.audit_log.record(
            organization_id=organization.id,
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditActionEnum.UPDATE,
            resource_type="organization",
            resource_id=organization.id,
            changes={"before": before, "after": changes},
        )
        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def delete(self, organization: Organization, *, actor: User) -> None:
        await self.organizations.soft_delete(organization)
        await self.audit_log.record(
            organization_id=organization.id,
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditActionEnum.DELETE,
            resource_type="organization",
            resource_id=organization.id,
        )
        await self.db.commit()

    async def upload_logo(
        self, organization: Organization, *, file: UploadFile, actor: User
    ) -> Organization:
        logo_url = await self.storage.save_logo(organization.id, file)
        organization = await self.organizations.update(organization, {"logo_url": logo_url})
        await self.audit_log.record(
            organization_id=organization.id,
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditActionEnum.UPDATE,
            resource_type="organization",
            resource_id=organization.id,
            changes={"logo_url": logo_url},
        )
        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def delete_logo(self, organization: Organization, *, actor: User) -> Organization:
        self.storage.delete_logo(organization.id)
        organization = await self.organizations.update(organization, {"logo_url": None})
        await self.audit_log.record(
            organization_id=organization.id,
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditActionEnum.UPDATE,
            resource_type="organization",
            resource_id=organization.id,
            changes={"logo_url": None},
        )
        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def list_members(
        self,
        organization_id: uuid.UUID,
        *,
        search: str | None = None,
        status: str | None = None,
        role_name: str | None = None,
        sort_by: str = "joined_at",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[User], int]:
        return await self.users.list_for_organization(
            organization_id,
            search=search,
            status=status,
            role_name=role_name,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size,
        )
