import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        return await self.db.scalar(select(Session).where(Session.id == session_id))

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        result = await self.db.scalars(
            select(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .order_by(Session.last_active_at.desc())
        )
        return list(result)

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        return len(await self.list_active_for_user(user_id))

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        ip_address: str | None,
        user_agent: str | None,
        device_info: dict | None,
        expires_at: datetime,
    ) -> Session:
        session = Session(
            user_id=user_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def touch(self, session: Session) -> None:
        session.last_active_at = datetime.now(session.expires_at.tzinfo)
        await self.db.flush()

    async def revoke(self, session: Session) -> None:
        session.is_active = False
        await self.db.flush()

    async def revoke_oldest(self, user_id: uuid.UUID) -> None:
        active = await self.list_active_for_user(user_id)
        if active:
            await self.revoke(active[-1])

    async def revoke_all_for_user(self, user_id: uuid.UUID, *, except_session_id: uuid.UUID | None = None) -> int:
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .values(is_active=False)
        )
        if except_session_id is not None:
            stmt = stmt.where(Session.id != except_session_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0
