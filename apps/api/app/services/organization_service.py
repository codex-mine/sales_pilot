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

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoleNameEnum
from app.models.identity.models import Organization, Role
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.role_repository import RoleRepository
from app.security.permissions import DEFAULT_ROLE_PERMISSIONS


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.organizations = OrganizationRepository(db)
        self.roles = RoleRepository(db)

    async def create_with_owner_role(self, name: str) -> tuple[Organization, Role]:
        slug = await self.organizations.generate_unique_slug(name)
        organization = await self.organizations.create(name=name, slug=slug)
        await self.seed_system_roles(organization.id)
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
