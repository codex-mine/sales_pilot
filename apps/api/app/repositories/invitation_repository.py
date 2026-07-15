import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrganizationInvitationStatusEnum
from app.models.identity.models import OrganizationInvitation


class InvitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, invitation_id: uuid.UUID) -> OrganizationInvitation | None:
        return await self.db.scalar(
            select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id)
        )

    async def get_by_hash(self, token_hash: str) -> OrganizationInvitation | None:
        return await self.db.scalar(
            select(OrganizationInvitation).where(OrganizationInvitation.token_hash == token_hash)
        )

    async def get_pending_for_email(
        self, organization_id: uuid.UUID, email: str
    ) -> OrganizationInvitation | None:
        return await self.db.scalar(
            select(OrganizationInvitation).where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email.lower(),
                OrganizationInvitation.status == OrganizationInvitationStatusEnum.PENDING,
            )
        )

    async def list_pending_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[OrganizationInvitation]:
        result = await self.db.scalars(
            select(OrganizationInvitation).where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.status == OrganizationInvitationStatusEnum.PENDING,
            )
        )
        return list(result)

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        role_id: uuid.UUID,
        invited_by: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> OrganizationInvitation:
        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=email.lower(),
            role_id=role_id,
            invited_by=invited_by,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()
        return invitation

    async def mark_accepted(self, invitation: OrganizationInvitation, accepted_by: uuid.UUID) -> None:
        invitation.status = OrganizationInvitationStatusEnum.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        invitation.accepted_by = accepted_by
        await self.db.flush()

    async def revoke(self, invitation: OrganizationInvitation) -> None:
        invitation.status = OrganizationInvitationStatusEnum.REVOKED
        invitation.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()

    @staticmethod
    def is_valid(invitation: OrganizationInvitation) -> bool:
        if invitation.status != OrganizationInvitationStatusEnum.PENDING:
            return False
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
