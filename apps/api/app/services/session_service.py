"""
Session + token-pair lifecycle: issuance, rotation, and revocation.

Two independent revocation mechanisms exist on purpose:
- `Session.is_active` is the authority for "is this login still allowed to
  refresh". Revoking a session (logout, "log out this device", admin action)
  immediately blocks the *next* refresh attempt tied to it, even though the
  already-issued refresh token JWT is still cryptographically valid — the
  session check happens before the token is trusted.
- `RefreshToken.revoked_at` / `replaced_by` guard the rotation chain itself:
  each refresh token is single-use. If a token is presented twice (the first
  use rotated it already), that's a signal of theft/replay, so we respond by
  revoking every session and refresh token the user has, not just this one.

`Session.expires_at` is an absolute ceiling: every rotated refresh token is
capped to it, so "remember me" extends how long you can stay logged in
without re-entering credentials, but never indefinitely — a stolen laptop's
session dies on schedule even if refreshes have been happening constantly.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import SessionExpiredError, TokenRevokedError
from app.models.identity.models import Session, User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.security.tokens import (
    AccessTokenClaims,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.services.rbac_service import RBACService


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.users = UserRepository(db)
        self.rbac = RBACService(db)

    async def _issue_claims(self, user: User, session_id: uuid.UUID) -> AccessTokenClaims:
        primary_role = await self.rbac.get_primary_role(user.id, user.organization_id)
        return AccessTokenClaims(
            user_id=str(user.id),
            organization_id=str(user.organization_id),
            workspace_id=str(user.organization_id),
            role_id=str(primary_role.id) if primary_role else None,
            role_name=primary_role.name if primary_role else None,
            permissions_version=user.permissions_version,
            session_id=str(session_id),
        )

    async def issue_token_pair(
        self,
        user: User,
        *,
        ip_address: str | None,
        user_agent: str | None,
        device_info: dict | None,
        remember_me: bool,
    ) -> tuple[str, str, Session]:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        session_days = (
            settings.session_remember_me_expire_days if remember_me else settings.session_expire_days
        )
        session_expires_at = now + timedelta(days=session_days)

        if await self.sessions.count_active_for_user(user.id) >= settings.max_active_sessions_per_user:
            await self.sessions.revoke_oldest(user.id)

        session = await self.sessions.create(
            user_id=user.id,
            organization_id=user.organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=session_expires_at,
        )

        access_token = create_access_token(await self._issue_claims(user, session.id))
        raw_refresh, _jti, refresh_expires_at = create_refresh_token(
            str(user.id), str(session.id), remember_me=remember_me
        )
        refresh_expires_at = min(refresh_expires_at, session_expires_at)
        await self.refresh_tokens.create(
            user_id=user.id, token_hash=hash_token(raw_refresh), expires_at=refresh_expires_at
        )
        return access_token, raw_refresh, session

    async def rotate(self, raw_refresh_token: str) -> tuple[str, str, Session, User]:
        payload = decode_token(raw_refresh_token, expected_type="refresh")
        token_hash = hash_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)

        if stored is None:
            raise TokenRevokedError()
        if not RefreshTokenRepository.is_valid(stored):
            # Reuse of an already-rotated/expired token: treat as theft and
            # burn every credential this user currently holds.
            await self.refresh_tokens.revoke_all_for_user(stored.user_id)
            await self.sessions.revoke_all_for_user(stored.user_id)
            raise TokenRevokedError(
                "This refresh token was already used. All sessions have been revoked for your protection."
            )

        session_id = uuid.UUID(payload["session_id"])
        session = await self.sessions.get_by_id(session_id)
        if session is None or not session.is_active:
            raise SessionExpiredError()
        session_expires_at = session.expires_at
        if session_expires_at.tzinfo is None:
            session_expires_at = session_expires_at.replace(tzinfo=timezone.utc)
        if session_expires_at <= datetime.now(timezone.utc):
            await self.sessions.revoke(session)
            raise SessionExpiredError()

        user = await self.users.get_by_id(uuid.UUID(payload["sub"]))
        if user is None:
            raise SessionExpiredError()

        access_token = create_access_token(await self._issue_claims(user, session.id))
        new_raw_refresh, _jti, new_expires_at = create_refresh_token(str(user.id), str(session.id))
        new_expires_at = min(new_expires_at, session_expires_at)
        new_hash = hash_token(new_raw_refresh)
        await self.refresh_tokens.revoke(stored, replaced_by=new_hash)
        await self.refresh_tokens.create(user_id=user.id, token_hash=new_hash, expires_at=new_expires_at)
        await self.sessions.touch(session)

        return access_token, new_raw_refresh, session, user

    async def revoke_session(self, session: Session) -> None:
        await self.sessions.revoke(session)

    async def revoke_all_sessions(self, user_id: uuid.UUID, *, except_session_id: uuid.UUID | None = None) -> int:
        return await self.sessions.revoke_all_for_user(user_id, except_session_id=except_session_id)
