"""
Per-organization outreach sender identity (Settings -> Email Sender).

Mirrors `app.services.ai.ai_settings_service.AISettingsService` exactly:
credentials live encrypted on an org-level Integration row
(integration_type="smtp", user_id NULL) and take precedence over the
platform-level `outreach_smtp_*` env fallback. Decrypted credentials never
leave the backend — every read path projects to booleans/non-secret fields.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.integration_repository import IntegrationRepository
from app.security.crypto import decrypt_secret, encrypt_secret

_INTEGRATION_TYPE = "smtp"


class EmailSenderSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integrations = IntegrationRepository(db)
        self.emails = EmailRepository(db)
        self.audit_log = AuditLogRepository(db)

    # ─── Credential resolution (used by EmailSendingService — never exposed via API) ─

    async def resolve_credentials(
        self, organization_id: uuid.UUID
    ) -> tuple[str, int, str | None, str | None, bool] | None:
        """Returns (host, port, username, password, use_tls), org-level
        Integration override first, platform env fallback second. None if
        neither is configured."""
        row = await self.integrations.get_org_level(organization_id, _INTEGRATION_TYPE)
        if row is not None and row.is_active:
            config = row.config or {}
            password = decrypt_secret(row.access_token_encrypted) if row.access_token_encrypted else None
            if config.get("host") and password:
                return (
                    config["host"], int(config.get("port", 587)), config.get("username"),
                    password, bool(config.get("use_tls", True)),
                )

        settings = get_settings()
        if settings.outreach_smtp_host and settings.outreach_smtp_password:
            return (
                settings.outreach_smtp_host, settings.outreach_smtp_port, settings.outreach_smtp_username,
                settings.outreach_smtp_password, settings.outreach_smtp_use_tls,
            )
        return None

    async def daily_send_limit(self, organization_id: uuid.UUID) -> int:
        """Org Integration override (`config.daily_send_limit`) first,
        platform default second — same override shape as credentials."""
        row = await self.integrations.get_org_level(organization_id, _INTEGRATION_TYPE)
        if row is not None and row.config and row.config.get("daily_send_limit"):
            return int(row.config["daily_send_limit"])
        return get_settings().outreach_daily_send_limit_default

    # ─── Settings read ──────────────────────────────────────────────────────────

    async def status(self, organization_id: uuid.UUID) -> dict:
        settings = get_settings()
        row = await self.integrations.get_org_level(organization_id, _INTEGRATION_TYPE)
        has_platform_fallback = bool(settings.outreach_smtp_host and settings.outreach_smtp_password)
        config = (row.config or {}) if row else {}
        is_connected = bool(row is not None and row.is_active and config.get("host") and row.access_token_encrypted)
        sent_today = await self.emails.count_sent_today(organization_id)
        return {
            "is_connected": is_connected,
            "integration_id": str(row.id) if row and is_connected else None,
            "host": config.get("host") if is_connected else None,
            "port": config.get("port") if is_connected else None,
            "username": config.get("username") if is_connected else None,
            "use_tls": config.get("use_tls") if is_connected else None,
            "has_platform_fallback": has_platform_fallback,
            "daily_send_limit": int(config.get("daily_send_limit") or settings.outreach_daily_send_limit_default),
            "sent_today": sent_today,
        }

    # ─── Settings write ─────────────────────────────────────────────────────────

    async def connect(
        self,
        *,
        organization_id: uuid.UUID,
        host: str,
        port: int,
        username: str | None,
        password: str,
        use_tls: bool,
        daily_send_limit: int | None,
        actor: User,
    ) -> None:
        if not host or not password:
            raise ValidationError(
                "Host and password are required.", errors={"host": ["Required."], "password": ["Required."]}
            )
        row = await self.integrations.get_org_level(organization_id, _INTEGRATION_TYPE)
        fields = {
            "access_token_encrypted": encrypt_secret(password),
            "config": {
                "host": host, "port": port, "username": username, "use_tls": use_tls,
                **({"daily_send_limit": daily_send_limit} if daily_send_limit else {}),
            },
            "is_active": True,
        }
        if row is None:
            await self.integrations.create(
                organization_id=organization_id, created_by=actor.id,
                integration_type=_INTEGRATION_TYPE, name="Outreach sending mailbox", **fields,
            )
        else:
            await self.integrations.update(row, fields, updated_by=actor.id)

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_sender_settings",
            changes={"event": "sender_identity_connected", "host": host},
        )
        await self.db.commit()

    async def disconnect(self, *, organization_id: uuid.UUID, integration_id: uuid.UUID, actor: User) -> None:
        row = await self.integrations.get_org_level(organization_id, _INTEGRATION_TYPE)
        if row is None or row.id != integration_id:
            raise NotFoundError("Sender identity not found.")
        await self.integrations.delete(row)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email_sender_settings",
            changes={"event": "sender_identity_disconnected"},
        )
        await self.db.commit()
