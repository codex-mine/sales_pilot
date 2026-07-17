import uuid

from sqlalchemy import func, insert, or_, select
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

    _MEMBER_SORT_COLUMNS = {
        "name": User.first_name,
        "email": User.email,
        "status": User.status,
        "joined_at": User.created_at,
        "last_active_at": User.last_login_at,
    }

    async def list_for_organization(
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
        """
        Members list for the Organization module. Eager-loads `roles` via
        `selectinload` (one extra batched query for all returned users, not
        one per row) so callers can read `user.roles` without N+1 queries.
        """
        conditions = [User.organization_id == organization_id, User.deleted_at.is_(None)]
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(User.first_name).like(like),
                    func.lower(User.last_name).like(like),
                    func.lower(User.email).like(like),
                )
            )
        if status:
            conditions.append(User.status == status)

        base_query = select(User).where(*conditions)
        count_query = select(func.count(func.distinct(User.id))).where(*conditions)
        if role_name:
            base_query = base_query.join(UserRole, UserRole.user_id == User.id).join(
                Role, Role.id == UserRole.role_id
            ).where(Role.name == role_name)
            count_query = count_query.join(UserRole, UserRole.user_id == User.id).join(
                Role, Role.id == UserRole.role_id
            ).where(Role.name == role_name)

        total = await self.db.scalar(count_query) or 0

        sort_column = self._MEMBER_SORT_COLUMNS.get(sort_by, User.created_at)
        order = sort_column.desc() if sort_desc else sort_column.asc()
        base_query = (
            base_query.options(selectinload(User.roles))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.scalars(base_query)
        return list(result.unique()), total
