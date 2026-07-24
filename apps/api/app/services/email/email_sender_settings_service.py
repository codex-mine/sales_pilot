"""
Per-organization outreach sender identity (Settings -> Email Sender / Sender
Mailbox Management).

Mirrors `app.services.ai.ai_settings_service.AISettingsService` exactly:
credentials live encrypted on org-level Integration rows
(integration_type="smtp", user_id NULL) and take precedence over the
platform-level `outreach_smtp_*` env fallback. Decrypted credentials never
leave the backend — every read path projects to booleans/non-secret fields.

**Multi-mailbox note**: an organization can now have MORE than one
`integration_type="smtp"` row (Sender Mailbox Management). No schema
migration was needed for this — every per-mailbox field the feature needs
already had a home on the existing `Integration` model: `name` (mailbox
nickname), `external_account_email` (the mailbox's own email address,
otherwise unused for SMTP), `is_active` (status), and `config` JSONB, which
now also carries `encryption_type`/`from_name`/`reply_to`/`is_default`
alongside the pre-existing `host`/`port`/`username`/`use_tls`/
`daily_send_limit` keys. The original single-mailbox methods
(`resolve_credentials`/`status`/`connect`/`disconnect`, all built on
`IntegrationRepository.get_org_level`'s "the one row" convention) are left
exactly as they were for backward compatibility; the multi-mailbox methods
below (`list_mailboxes`/`create_mailbox`/... ) are additive and operate on
`list_org_level_by_type` instead.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.models.remaining_domains import Integration
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.integration_repository import IntegrationRepository
from app.schemas.email_sending import CreateSenderMailboxRequest, UpdateSenderMailboxRequest
from app.security.crypto import decrypt_secret, encrypt_secret
from app.services.email.sender_client import test_smtp_connection

_INTEGRATION_TYPE = "smtp"


class EmailSenderSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integrations = IntegrationRepository(db)
        self.emails = EmailRepository(db)
        self.audit_log = AuditLogRepository(db)

    # ─── Credential resolution (used by EmailSendingService — never exposed via API) ─

    async def resolve_credentials(
        self, organization_id: uuid.UUID, *, mailbox_id: uuid.UUID | None = None
    ) -> tuple[str, int, str | None, str | None, bool, str] | None:
        """Returns (host, port, username, password, use_tls, encryption_type).

        - `mailbox_id` given: resolve exactly that mailbox (a specific Email
          row's `sender_mailbox_id`, e.g. from a manually-composed or
          per-step-configured send).
        - `mailbox_id` omitted: resolve the org's default mailbox — the one
          with `config.is_default = True`, or (backward compatibility for
          orgs that connected a single mailbox before this feature existed
          and so never got an explicit `is_default` flag) the sole mailbox
          if exactly one exists, or the first-created one if several exist
          and somehow none is flagged default.
        - Nothing configured at all: platform env fallback, same as before.
        """
        row: Integration | None = None
        if mailbox_id is not None:
            row = await self.integrations.get_by_id(mailbox_id, organization_id)
            if row is not None and row.integration_type != _INTEGRATION_TYPE:
                row = None
        else:
            candidates = [
                r for r in await self.integrations.list_org_level_by_type(organization_id, _INTEGRATION_TYPE)
                if r.is_active
            ]
            row = next((r for r in candidates if (r.config or {}).get("is_default")), None)
            if row is None and candidates:
                row = candidates[0]

        if row is not None and row.is_active:
            config = row.config or {}
            password = decrypt_secret(row.access_token_encrypted) if row.access_token_encrypted else None
            if config.get("host") and password:
                use_tls = bool(config.get("use_tls", True))
                encryption_type = config.get("encryption_type") or ("starttls" if use_tls else "none")
                return (
                    config["host"], int(config.get("port", 587)), config.get("username"),
                    password, use_tls, encryption_type,
                )

        settings = get_settings()
        if settings.outreach_smtp_host and settings.outreach_smtp_password:
            return (
                settings.outreach_smtp_host, settings.outreach_smtp_port, settings.outreach_smtp_username,
                settings.outreach_smtp_password, settings.outreach_smtp_use_tls,
                "starttls" if settings.outreach_smtp_use_tls else "none",
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

    # ─── Sender Mailbox Management (multi-mailbox) ─────────────────────────────

    async def list_mailboxes(self, organization_id: uuid.UUID) -> list[Integration]:
        return await self.integrations.list_org_level_by_type(organization_id, _INTEGRATION_TYPE)

    async def require_mailbox(self, organization_id: uuid.UUID, mailbox_id: uuid.UUID) -> Integration:
        row = await self.integrations.get_by_id(mailbox_id, organization_id)
        if row is None or row.integration_type != _INTEGRATION_TYPE:
            raise NotFoundError("Sender mailbox not found.")
        return row

    async def get_mailbox_identity(self, organization_id: uuid.UUID, mailbox_id: uuid.UUID) -> tuple[str, str | None, str | None]:
        """(from_email, from_name, reply_to) for a chosen mailbox — used by
        the manual email composer (Phase X Issue 08) to fill in sender
        identity fields once a mailbox is picked, without duplicating the
        `config` JSONB unpacking logic that already lives in
        `serialize_sender_mailbox`."""
        mailbox = await self.require_mailbox(organization_id, mailbox_id)
        config = mailbox.config or {}
        from_email = mailbox.external_account_email or config.get("username") or ""
        return from_email, config.get("from_name"), config.get("reply_to")

    async def create_mailbox(
        self, organization_id: uuid.UUID, *, payload: CreateSenderMailboxRequest, actor: User
    ) -> Integration:
        # "Before saving a mailbox: run a real SMTP connection test... if
        # connection fails, do NOT save." `test_smtp_connection` raises
        # `ValidationError` on any failure, which propagates straight out of
        # this method before anything touches the database.
        await test_smtp_connection(
            host=payload.host, port=payload.port, username=payload.username, password=payload.password,
            encryption_type=payload.encryption_type,
        )

        existing = await self.list_mailboxes(organization_id)
        is_default = payload.is_default or not existing  # the org's first mailbox is always the default

        config: dict[str, Any] = {
            "host": payload.host, "port": payload.port, "username": payload.username,
            "use_tls": payload.encryption_type != "none", "encryption_type": payload.encryption_type,
            "from_name": payload.from_name, "reply_to": payload.reply_to, "is_default": is_default,
        }
        if payload.daily_send_limit:
            config["daily_send_limit"] = payload.daily_send_limit

        if is_default:
            await self._clear_other_defaults(existing, actor=actor)

        mailbox = await self.integrations.create(
            organization_id=organization_id, created_by=actor.id, integration_type=_INTEGRATION_TYPE,
            name=payload.name, external_account_email=payload.email_address,
            access_token_encrypted=encrypt_secret(payload.password), config=config, is_active=True,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="sender_mailbox", resource_id=mailbox.id,
            changes={"event": "sender_mailbox_created", "name": payload.name, "host": payload.host},
        )
        await self.db.commit()
        return await self.require_mailbox(organization_id, mailbox.id)

    async def update_mailbox(
        self, mailbox: Integration, *, payload: UpdateSenderMailboxRequest, actor: User
    ) -> Integration:
        config = dict(mailbox.config or {})
        changes: dict[str, Any] = {}
        set_fields = payload.model_fields_set

        credential_fields = {"host", "port", "username", "password", "encryption_type"}
        if credential_fields & set_fields:
            # Re-verify before persisting any credential-affecting change —
            # same "do NOT save on failure" rule as creation.
            test_host = payload.host if payload.host is not None else config.get("host")
            test_port = payload.port if payload.port is not None else int(config.get("port", 587))
            test_username = payload.username if "username" in set_fields else config.get("username")
            test_password = (
                payload.password if payload.password is not None
                else (decrypt_secret(mailbox.access_token_encrypted) if mailbox.access_token_encrypted else None)
            )
            test_encryption = payload.encryption_type or config.get("encryption_type") or "starttls"
            if not test_password:
                raise ValidationError("A password is required to verify this mailbox.")
            await test_smtp_connection(
                host=test_host, port=test_port, username=test_username, password=test_password,
                encryption_type=test_encryption,
            )
            config.update(
                host=test_host, port=test_port, username=test_username,
                encryption_type=test_encryption, use_tls=test_encryption != "none",
            )
            if payload.password is not None:
                changes["access_token_encrypted"] = encrypt_secret(payload.password)

        if "name" in set_fields:
            changes["name"] = payload.name
        if "email_address" in set_fields:
            changes["external_account_email"] = payload.email_address
        if "from_name" in set_fields:
            config["from_name"] = payload.from_name
        if "reply_to" in set_fields:
            config["reply_to"] = payload.reply_to
        if "daily_send_limit" in set_fields:
            if payload.daily_send_limit:
                config["daily_send_limit"] = payload.daily_send_limit
            else:
                config.pop("daily_send_limit", None)
        if "is_active" in set_fields:
            changes["is_active"] = payload.is_active

        changes["config"] = config
        mailbox = await self.integrations.update(mailbox, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=mailbox.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="sender_mailbox", resource_id=mailbox.id,
            changes={"event": "sender_mailbox_updated"},
        )
        await self.db.commit()
        return await self.require_mailbox(mailbox.organization_id, mailbox.id)

    async def set_default_mailbox(self, organization_id: uuid.UUID, mailbox_id: uuid.UUID, *, actor: User) -> Integration:
        mailbox = await self.require_mailbox(organization_id, mailbox_id)
        existing = await self.list_mailboxes(organization_id)
        await self._clear_other_defaults(existing, exclude_id=mailbox.id, actor=actor)
        config = dict(mailbox.config or {})
        config["is_default"] = True
        mailbox = await self.integrations.update(mailbox, {"config": config}, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="sender_mailbox", resource_id=mailbox.id,
            changes={"event": "sender_mailbox_set_default"},
        )
        await self.db.commit()
        return await self.require_mailbox(organization_id, mailbox.id)

    async def delete_mailbox(self, organization_id: uuid.UUID, mailbox_id: uuid.UUID, *, actor: User) -> None:
        mailbox = await self.require_mailbox(organization_id, mailbox_id)
        await self.integrations.delete(mailbox)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="sender_mailbox", resource_id=mailbox_id,
            changes={"event": "sender_mailbox_deleted", "name": mailbox.name},
        )
        await self.db.commit()

    async def _clear_other_defaults(
        self, mailboxes: list[Integration], *, exclude_id: uuid.UUID | None = None, actor: User
    ) -> None:
        for other in mailboxes:
            if other.id == exclude_id or not (other.config or {}).get("is_default"):
                continue
            config = dict(other.config or {})
            config["is_default"] = False
            await self.integrations.update(other, {"config": config}, updated_by=actor.id)
