import uuid

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity.models import Permission, Role, RolePermission


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self.db.scalar(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        )

    async def get_by_name(self, organization_id: uuid.UUID, name: str) -> Role | None:
        return await self.db.scalar(
            select(Role).where(Role.organization_id == organization_id, Role.name == name)
        )

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Role]:
        result = await self.db.scalars(
            select(Role).where(Role.organization_id == organization_id).order_by(Role.name)
        )
        return list(result)

    async def create(
        self, *, organization_id: uuid.UUID, name: str, is_system: bool = False, description: str | None = None
    ) -> Role:
        role = Role(
            organization_id=organization_id, name=name, is_system=is_system, description=description
        )
        self.db.add(role)
        await self.db.flush()
        return role

    async def get_or_create_permission(self, resource: str, action: str) -> Permission:
        permission = await self.db.scalar(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        if permission is None:
            permission = Permission(resource=resource, action=action)
            self.db.add(permission)
            await self.db.flush()
        return permission

    async def set_permissions(self, role: Role, permissions: list[Permission]) -> None:
        """
        Replaces the role's permission set via direct association-table writes
        rather than assigning to `role.permissions`. Assigning to that ORM
        collection triggers back_populates syncing on `Permission.roles` for
        each permission, which requires lazily loading that (unloaded)
        reverse collection — not awaitable mid-request under asyncio, and the
        exact operation this method is called with fresh, never-loaded
        Permission rows from `get_or_create_permission`.
        """
        await self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        if permissions:
            await self.db.execute(
                insert(RolePermission),
                [{"role_id": role.id, "permission_id": p.id} for p in permissions],
            )
        await self.db.flush()
