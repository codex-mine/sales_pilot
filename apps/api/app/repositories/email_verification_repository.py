import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import EmailVerificationToken


class EmailVerificationTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return await self.db.scalar(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        result = await self.db.scalars(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.verified_at.is_(None),
            )
        )
        now = datetime.now(timezone.utc)
        for token in result:
            token.verified_at = now
        await self.db.flush()

    @staticmethod
    def is_valid(token: EmailVerificationToken) -> bool:
        if token.verified_at is not None:
            return False
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)

    async def mark_verified(self, token: EmailVerificationToken) -> None:
        token.verified_at = datetime.now(timezone.utc)
        await self.db.flush()
