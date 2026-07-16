"""
Core authentication business logic: registration, login, password lifecycle,
and email verification. Session/token issuance is delegated to
SessionService; RBAC seeding is delegated to OrganizationService; this class
orchestrates them and owns the account-status/audit rules.
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import (
    AccountSuspendedError,
    AuthenticationError,
    ConflictError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
)
from app.models.enums import AuditActionEnum, UserStatusEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_verification_repository import (
    EmailVerificationTokenRepository,
)
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.security.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.security.rate_limit import (
    check_account_lockout,
    check_login_rate_limit,
    clear_login_failures,
    record_failed_login,
)
from app.security.tokens import create_opaque_token, hash_token
from app.services.email_service import send_password_reset_email, send_verification_email
from app.services.organization_service import OrganizationService
from app.services.session_service import SessionService

logger = structlog.get_logger(__name__)

# Statuses that may never authenticate, each with a distinct client-facing error
# so the frontend can render "contact support" vs "reactivate" vs "not found".
_BLOCKED_STATUSES = {
    UserStatusEnum.SUSPENDED: "This account has been suspended. Contact your administrator.",
    UserStatusEnum.DISABLED: "This account has been disabled.",
    UserStatusEnum.DELETED: "This account no longer exists.",
    UserStatusEnum.INACTIVE: "This account is inactive. Contact your administrator.",
}


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis
        self.users = UserRepository(db)
        self.password_reset_tokens = PasswordResetTokenRepository(db)
        self.email_verification_tokens = EmailVerificationTokenRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.organizations = OrganizationService(db)
        self.sessions = SessionService(db)

    # ─── Registration ──────────────────────────────────────────────────────────

    async def register(
        self,
        payload: RegisterRequest,
        *,
        ip_address: str | None,
        user_agent: str | None
    ) -> tuple[User, str]:
        """Returns (user, raw_email_verification_token)."""
        if await self.users.get_by_email(payload.email):
            raise ConflictError("An account with this email already exists.")

        violations = validate_password_strength(payload.password)
        if violations:
            raise ConflictError(
                "Password does not meet the required strength.",
                errors={"password": violations},
            )

        organization, owner_role = await self.organizations.create_with_owner_role(
            payload.organization_name
        )
        user = await self.users.create(
            organization_id=organization.id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            status=UserStatusEnum.PENDING_VERIFICATION,
        )
        await self.users.assign_role(user, owner_role)

        raw_token = await self._issue_email_verification_token(user)

        await self.audit_log.record(
            organization_id=organization.id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.REGISTER,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()
        await self.db.refresh(user)
        await send_verification_email(to=user.email, first_name=user.first_name, token=raw_token)
        return user, raw_token

    # ─── Login ──────────────────────────────────────────────────────────────────

    async def authenticate(
        self, payload: LoginRequest, *, ip_address: str | None, user_agent: str | None
    ) -> User:
        if ip_address:
            await check_login_rate_limit(self.redis, ip_address)

        user = await self.users.get_by_email(payload.email)
        if user is None:
            # Constant-shape failure: don't reveal whether the email exists.
            logger.info("login_failed", reason="unknown_email", ip_address=ip_address)
            raise InvalidCredentialsError()

        await check_account_lockout(self.redis, str(user.id))

        if user.status in _BLOCKED_STATUSES:
            await self.audit_log.record(
                organization_id=user.organization_id,
                actor_id=user.id,
                actor_email=user.email,
                action=AuditActionEnum.LOGIN_FAILED,
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                changes={"reason": "account_status_blocked", "status": user.status},
            )
            await self.db.commit()
            raise AccountSuspendedError(_BLOCKED_STATUSES[user.status])

        if not user.password_hash or not verify_password(
            payload.password, user.password_hash
        ):
            await record_failed_login(self.redis, str(user.id))
            await self.audit_log.record(
                organization_id=user.organization_id,
                actor_id=user.id,
                actor_email=user.email,
                action=AuditActionEnum.LOGIN_FAILED,
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()
            raise InvalidCredentialsError()

        await clear_login_failures(self.redis, str(user.id))
        user.last_login_at = datetime.now(timezone.utc)
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.LOGIN,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    def require_verified_email(self, user: User) -> None:
        if not user.email_verified:
            raise EmailNotVerifiedError()

    # ─── Password lifecycle ────────────────────────────────────────────────────

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not user.password_hash or not verify_password(
            payload.current_password, user.password_hash
        ):
            raise InvalidCredentialsError("Current password is incorrect.")
        violations = validate_password_strength(payload.new_password)
        if violations:
            raise ConflictError(
                "Password does not meet the required strength.",
                errors={"new_password": violations},
            )

        user.password_hash = hash_password(payload.new_password)
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.PASSWORD_CHANGED,
            resource_type="user",
            resource_id=user.id,
        )
        await self.db.commit()

    async def request_password_reset(self, email: str) -> str | None:
        """Returns the raw reset token, or None if no account matches (caller must respond identically either way)."""
        user = await self.users.get_by_email(email)
        if user is None:
            return None

        await self.password_reset_tokens.invalidate_all_for_user(user.id)
        raw_token = create_opaque_token()
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        await self.password_reset_tokens.create(
            user_id=user.id, token_hash=hash_token(raw_token), expires_at=expires_at
        )
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.PASSWORD_RESET_REQUESTED,
            resource_type="user",
            resource_id=user.id,
        )
        await self.db.commit()
        await send_password_reset_email(to=user.email, first_name=user.first_name, token=raw_token)
        return raw_token

    async def reset_password(self, raw_token: str, new_password: str) -> User:
        violations = validate_password_strength(new_password)
        if violations:
            raise ConflictError(
                "Password does not meet the required strength.",
                errors={"password": violations},
            )

        token_row = await self.password_reset_tokens.get_by_hash(hash_token(raw_token))
        if token_row is None or not PasswordResetTokenRepository.is_valid(token_row):
            raise AuthenticationError(
                "This password reset link is invalid or has expired."
            )

        user = await self.users.get_by_id(token_row.user_id)
        if user is None:
            raise AuthenticationError(
                "This password reset link is invalid or has expired."
            )

        user.password_hash = hash_password(new_password)
        await self.password_reset_tokens.mark_used(token_row)
        # A password reset means the old password may have been compromised —
        # every existing session and refresh token must die immediately.
        await self.sessions.revoke_all_sessions(user.id)
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.PASSWORD_RESET_COMPLETED,
            resource_type="user",
            resource_id=user.id,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ─── Email verification ────────────────────────────────────────────────────

    async def _issue_email_verification_token(self, user: User) -> str:
        await self.email_verification_tokens.invalidate_all_for_user(user.id)
        raw_token = create_opaque_token()
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        await self.email_verification_tokens.create(
            user_id=user.id, token_hash=hash_token(raw_token), expires_at=expires_at
        )
        return raw_token

    async def resend_verification(self, user: User) -> str:
        raw_token = await self._issue_email_verification_token(user)
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.EMAIL_VERIFICATION_REQUESTED,
            resource_type="user",
            resource_id=user.id,
        )
        await self.db.commit()
        await send_verification_email(to=user.email, first_name=user.first_name, token=raw_token)
        return raw_token

    async def verify_email(self, raw_token: str) -> User:
        token_row = await self.email_verification_tokens.get_by_hash(
            hash_token(raw_token)
        )
        if token_row is None or not EmailVerificationTokenRepository.is_valid(
            token_row
        ):
            raise AuthenticationError(
                "This verification link is invalid or has expired."
            )

        user = await self.users.get_by_id(token_row.user_id)
        if user is None:
            raise AuthenticationError(
                "This verification link is invalid or has expired."
            )

        user.email_verified = True
        if user.status == UserStatusEnum.PENDING_VERIFICATION:
            user.status = UserStatusEnum.ACTIVE
        await self.email_verification_tokens.mark_verified(token_row)
        await self.audit_log.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.EMAIL_VERIFIED,
            resource_type="user",
            resource_id=user.id,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user
