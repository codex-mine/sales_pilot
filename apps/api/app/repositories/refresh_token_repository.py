import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(token)
        await self.db.flush()
        return token

    async def revoke(self, token: RefreshToken, *, replaced_by: str | None = None) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        token.replaced_by = replaced_by
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        result = await self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
        now = datetime.now(timezone.utc)
        for token in result:
            token.revoked_at = now
        await self.db.flush()

    @staticmethod
    def is_valid(token: RefreshToken) -> bool:
        if token.revoked_at is not None:
            return False
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
