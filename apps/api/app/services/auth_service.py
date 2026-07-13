from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.entities import PasswordResetToken, RefreshToken, User, VerificationToken
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, create_opaque_token, hash_token

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: RegisterRequest) -> tuple[User, str]:
        email = str(payload.email).lower()
        if await self.db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        user = User(email=email, password_hash=hash_password(payload.password), full_name=payload.full_name)
        self.db.add(user)
        await self.db.flush()
        verification = create_opaque_token()
        self.db.add(VerificationToken(user_id=user.id, token_hash=hash_token(verification), expires_at=self._expires(hours=24)))
        await self.db.commit()
        await self.db.refresh(user)
        return user, verification

    async def authenticate(self, payload: LoginRequest) -> User:
        user = await self.db.scalar(select(User).where(User.email == str(payload.email).lower()))
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
        if not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user")
        return user

    async def issue_tokens(self, user: User) -> tuple[str, str]:
        raw_refresh = create_opaque_token()
        self.db.add(RefreshToken(user_id=user.id, token_hash=hash_token(raw_refresh), expires_at=self._expires(days=get_settings().jwt_refresh_token_expire_days)))
        await self.db.commit()
        return create_access_token(str(user.id)), raw_refresh

    async def refresh(self, raw_token: str) -> tuple[str, str]:
        token = await self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
        if not token or token.revoked_at or token.expires_at <= self._now():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        user = await self.db.get(User, token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user")
        token.revoked_at = self._now()  # rotation prevents replay.
        return await self.issue_tokens(user)

    async def revoke(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        token = await self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
        if token and not token.revoked_at:
            token.revoked_at = self._now()
            await self.db.commit()

    async def request_password_reset(self, email: str) -> str | None:
        user = await self.db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            return None
        raw_token = create_opaque_token()
        self.db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw_token), expires_at=self._expires(hours=1)))
        await self.db.commit()
        return raw_token

    async def reset_password(self, raw_token: str, password: str) -> None:
        token = await self.db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token)))
        if not token or token.used_at or token.expires_at <= self._now():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
        user = await self.db.get(User, token.user_id)
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token")
        user.password_hash = hash_password(password)
        token.used_at = self._now()
        await self._revoke_user_tokens(user.id)
        await self.db.commit()

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self._revoke_user_tokens(user.id)
        await self.db.commit()

    async def verify_email(self, raw_token: str) -> None:
        token = await self.db.scalar(select(VerificationToken).where(VerificationToken.token_hash == hash_token(raw_token)))
        if not token or token.expires_at <= self._now():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification token")
        user = await self.db.get(User, token.user_id)
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification token")
        user.is_verified = True
        await self.db.delete(token)
        await self.db.commit()

    async def _revoke_user_tokens(self, user_id: object) -> None:
        tokens = (await self.db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)))).all()
        for token in tokens:
            token.revoked_at = self._now()

    @staticmethod
    def _now() -> datetime: return datetime.now(timezone.utc)
    @classmethod
    def _expires(cls, *, hours: int = 0, days: int = 0) -> datetime: return cls._now() + timedelta(hours=hours, days=days)