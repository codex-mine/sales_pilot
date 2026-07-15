"""
Organization invitation flow: invite -> accept -> membership + role assignment.

See OrganizationInvitation's docstring in app/models/identity/models.py for
why "accept" only fully supports onboarding a brand-new email address today:
`User.organization_id` is singular (one primary org per user) until a V2
`OrganizationMembership` M:M table exists. Inviting an email that already has
an account anywhere is rejected with a clear, actionable error instead of
silently doing the wrong thing.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import AuthenticationError, ConflictError, NotFoundError
from app.models.enums import AuditActionEnum, UserStatusEnum
from app.models.identity.models import OrganizationInvitation, User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.security.passwords import hash_password, validate_password_strength
from app.security.tokens import create_opaque_token, hash_token


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.invitations = InvitationRepository(db)
        self.roles = RoleRepository(db)
        self.users = UserRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def invite(
        self, *, organization_id: uuid.UUID, email: str, role_id: uuid.UUID, invited_by: uuid.UUID
    ) -> tuple[OrganizationInvitation, str]:
        if await self.users.get_by_email(email):
            raise ConflictError("A user with this email already has an account.")
        if await self.invitations.get_pending_for_email(organization_id, email):
            raise ConflictError("An invitation is already pending for this email.")
        if await self.roles.get_by_id(role_id) is None:
            raise NotFoundError("Role not found.")

        raw_token = create_opaque_token()
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.invitation_token_expire_days)
        invitation = await self.invitations.create(
            organization_id=organization_id,
            email=email,
            role_id=role_id,
            invited_by=invited_by,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        await self.audit_log.record(
            organization_id=organization_id,
            actor_id=invited_by,
            actor_email=None,
            action=AuditActionEnum.INVITATION_SENT,
            resource_type="organization_invitation",
            resource_id=invitation.id,
        )
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation, raw_token

    async def accept(
        self, raw_token: str, *, first_name: str, last_name: str, password: str
    ) -> User:
        invitation = await self.invitations.get_by_hash(hash_token(raw_token))
        if invitation is None or not InvitationRepository.is_valid(invitation):
            raise AuthenticationError("This invitation is invalid or has expired.")

        if await self.users.get_by_email(invitation.email):
            raise ConflictError(
                "An account with this email already exists. Multi-organization membership "
                "for existing users is not yet supported — please log in to your existing account."
            )

        violations = validate_password_strength(password)
        if violations:
            raise ConflictError("Password does not meet the required strength.", errors={"password": violations})

        role = await self.roles.get_by_id(invitation.role_id)
        if role is None:
            raise NotFoundError("The role for this invitation no longer exists.")

        user = await self.users.create(
            organization_id=invitation.organization_id,
            email=invitation.email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            status=UserStatusEnum.ACTIVE,
        )
        user.email_verified = True  # invitation to a known email is itself a verification channel
        await self.users.assign_role(user, role)
        await self.invitations.mark_accepted(invitation, user.id)
        await self.audit_log.record(
            organization_id=invitation.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action=AuditActionEnum.INVITATION_ACCEPTED,
            resource_type="organization_invitation",
            resource_id=invitation.id,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def revoke(self, invitation: OrganizationInvitation, *, revoked_by: uuid.UUID) -> None:
        await self.invitations.revoke(invitation)
        await self.audit_log.record(
            organization_id=invitation.organization_id,
            actor_id=revoked_by,
            actor_email=None,
            action=AuditActionEnum.INVITATION_REVOKED,
            resource_type="organization_invitation",
            resource_id=invitation.id,
        )
        await self.db.commit()

    async def list_pending(self, organization_id: uuid.UUID) -> list[OrganizationInvitation]:
        return await self.invitations.list_pending_for_organization(organization_id)
