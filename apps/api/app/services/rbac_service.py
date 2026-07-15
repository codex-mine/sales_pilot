"""
Permission resolution. This is the *only* place that turns a user's role
assignments into a permission set — `require_permission` in
app/auth/dependencies.py calls straight into here on every request rather
than trusting anything in the JWT, per "never trust frontend claims."
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Permission, Role, RolePermission, UserRole
from app.security.permissions import permission_key, role_priority


class RBACService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_roles_for_user(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> list[Role]:
        result = await self.db.scalars(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, UserRole.organization_id == organization_id)
        )
        return list(result)

    async def get_primary_role(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> Role | None:
        roles = await self.get_roles_for_user(user_id, organization_id)
        if not roles:
            return None
        return min(roles, key=lambda r: role_priority(r.name))

    async def get_permission_keys(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> set[str]:
        result = await self.db.execute(
            select(Permission.resource, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, UserRole.organization_id == organization_id)
        )
        return {permission_key(resource, action) for resource, action in result.all()}

    async def has_permission(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, resource: str, action: str
    ) -> bool:
        keys = await self.get_permission_keys(user_id, organization_id)
        return permission_key(resource, action) in keys or permission_key(resource, "manage") in keys

    async def has_role(self, user_id: uuid.UUID, organization_id: uuid.UUID, role_name: str) -> bool:
        roles = await self.get_roles_for_user(user_id, organization_id)
        return any(role.name == role_name for role in roles)
