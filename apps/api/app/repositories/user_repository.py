import uuid

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity.models import Role, User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.scalar(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )

    async def get_by_email(self, email: str) -> User | None:
        return await self.db.scalar(
            select(User).options(selectinload(User.roles)).where(User.email == email.lower())
        )

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        password_hash: str | None,
        first_name: str,
        last_name: str,
        status: str,
    ) -> User:
        user = User(
            organization_id=organization_id,
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            status=status,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def assign_role(self, user: User, role: Role) -> None:
        """
        Inserts directly into the user_roles association table instead of
        appending to `user.roles` — that ORM collection append triggers
        back_populates syncing on `Role.users`, which would lazily load that
        (likely-unloaded) reverse collection and fail under asyncio.
        """
        existing = await self.db.scalar(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if existing is None:
            await self.db.execute(
                insert(UserRole),
                [{"user_id": user.id, "role_id": role.id, "organization_id": user.organization_id}],
            )
            user.permissions_version += 1
            await self.db.flush()

    async def bump_permissions_version(self, user: User) -> None:
        user.permissions_version += 1
        await self.db.flush()
