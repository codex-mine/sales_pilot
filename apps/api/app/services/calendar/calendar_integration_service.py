"""
Google Calendar connect/disconnect (Settings -> Calendar Integration).
Always a personal, user-level Integration row (`user_id` set — see the
Integration model's own docstring), never organization-wide. Mirrors
`AISettingsService`/`EmailSenderSettingsService`'s shape: credentials live
encrypted on an Integration row, decrypted values never leave the backend.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.integration_repository import IntegrationRepository
from app.security.crypto import encrypt_secret
from app.services.calendar.google_oauth import build_authorization_url, exchange_code_for_tokens

INTEGRATION_TYPE = "google_calendar"


class CalendarIntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integrations = IntegrationRepository(db)
        self.audit_log = AuditLogRepository(db)

    def build_connect_url(self, state: str) -> str:
        return build_authorization_url(state)

    async def handle_callback(self, *, organization_id: uuid.UUID, user: User, code: str) -> None:
        token_set = exchange_code_for_tokens(code)
        row = await self.integrations.get_user_level(organization_id, user.id, INTEGRATION_TYPE)

        fields = {
            "access_token_encrypted": encrypt_secret(token_set.access_token),
            "refresh_token_encrypted": encrypt_secret(token_set.refresh_token),
            "token_expires_at": token_set.expires_at,
            "scopes": token_set.scopes,
            "external_account_email": token_set.account_email,
            "external_account_id": token_set.account_email,
            "name": token_set.account_email or "Google Calendar",
            "is_active": True,
        }
        if row is None:
            await self.integrations.create(
                organization_id=organization_id, created_by=user.id, user_id=user.id,
                integration_type=INTEGRATION_TYPE, **fields,
            )
        else:
            await self.integrations.update(row, fields, updated_by=user.id)

        await self.audit_log.record(
            organization_id=organization_id, actor_id=user.id, actor_email=user.email,
            action=AuditActionEnum.UPDATE, resource_type="calendar_integration",
            changes={"event": "google_calendar_connected", "account_email": token_set.account_email},
        )
        await self.db.commit()

    async def status(self, organization_id: uuid.UUID, user: User) -> dict:
        row = await self.integrations.get_user_level(organization_id, user.id, INTEGRATION_TYPE)
        is_connected = bool(
            row is not None and row.is_active and row.access_token_encrypted and row.refresh_token_encrypted
        )
        return {
            "is_connected": is_connected,
            "account_email": row.external_account_email if is_connected and row else None,
            "connected_at": row.created_at if is_connected and row else None,
        }

    async def disconnect(self, organization_id: uuid.UUID, user: User) -> None:
        row = await self.integrations.get_user_level(organization_id, user.id, INTEGRATION_TYPE)
        if row is None:
            raise NotFoundError("Google Calendar is not connected.")
        await self.integrations.delete(row)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=user.id, actor_email=user.email,
            action=AuditActionEnum.UPDATE, resource_type="calendar_integration",
            changes={"event": "google_calendar_disconnected"},
        )
        await self.db.commit()
