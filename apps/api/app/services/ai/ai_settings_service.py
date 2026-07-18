"""
Per-organization AI provider configuration (AI -> Settings).

API keys live encrypted on org-level Integration rows (user_id NULL,
integration_type = provider name) and take precedence over the platform-level
env fallbacks in Settings. Decrypted keys never leave the backend — every
read path projects to `has_key: bool`.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import AuditActionEnum, LLMProviderEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.integration_repository import IntegrationRepository
from app.security.crypto import decrypt_secret, encrypt_secret

# Provider value <-> Integration.integration_type value. GOOGLE stores as
# "gemini" and LOCAL as "ollama" so the settings UI speaks product names.
PROVIDER_INTEGRATION_TYPES: dict[LLMProviderEnum, str] = {
    LLMProviderEnum.OPENAI: "openai",
    LLMProviderEnum.ANTHROPIC: "anthropic",
    LLMProviderEnum.GROQ: "groq",
    LLMProviderEnum.GOOGLE: "gemini",
    LLMProviderEnum.LOCAL: "ollama",
}
CONFIGURABLE_PROVIDERS: list[LLMProviderEnum] = list(PROVIDER_INTEGRATION_TYPES)


class AISettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integrations = IntegrationRepository(db)
        self.audit_log = AuditLogRepository(db)

    # ─── Key resolution (used by AIJobService — never exposed via API) ────────

    async def resolve_credentials(
        self, organization_id: uuid.UUID, provider: LLMProviderEnum
    ) -> tuple[str | None, str | None]:
        """Returns (api_key, base_url): org-level Integration override first,
        platform env fallback second."""
        settings = get_settings()
        integration_type = PROVIDER_INTEGRATION_TYPES.get(provider)
        row = (
            await self.integrations.get_org_level(organization_id, integration_type)
            if integration_type
            else None
        )
        if row is not None and row.is_active:
            api_key = decrypt_secret(row.access_token_encrypted) if row.access_token_encrypted else None
            base_url = (row.config or {}).get("base_url")
            if api_key or base_url:
                return api_key, base_url

        fallback_keys = {
            LLMProviderEnum.OPENAI: settings.openai_api_key,
            LLMProviderEnum.ANTHROPIC: settings.anthropic_api_key,
            LLMProviderEnum.GROQ: settings.groq_api_key,
            LLMProviderEnum.GOOGLE: settings.gemini_api_key,
        }
        return fallback_keys.get(provider), settings.ollama_base_url

    # ─── Settings read (boolean projections only) ─────────────────────────────

    async def provider_statuses(self, organization_id: uuid.UUID) -> list[dict]:
        settings = get_settings()
        org_rows = {
            row.integration_type: row for row in await self.integrations.list_org_level(organization_id)
        }
        env_fallbacks = {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "groq": bool(settings.groq_api_key),
            "gemini": bool(settings.gemini_api_key),
            "ollama": bool(settings.ollama_base_url),
        }
        statuses = []
        for provider, integration_type in PROVIDER_INTEGRATION_TYPES.items():
            row = org_rows.get(integration_type)
            has_org_key = bool(
                row is not None
                and row.is_active
                and (row.access_token_encrypted or (row.config or {}).get("base_url"))
            )
            statuses.append(
                {
                    "provider": provider.value,
                    "integration_type": integration_type,
                    "has_key": has_org_key or env_fallbacks[integration_type],
                    "has_org_key": has_org_key,
                    "has_platform_fallback": env_fallbacks[integration_type],
                }
            )
        return statuses

    # ─── Settings write ───────────────────────────────────────────────────────

    async def set_provider_key(
        self,
        *,
        organization_id: uuid.UUID,
        provider: LLMProviderEnum,
        api_key: str | None,
        base_url: str | None,
        actor: User,
    ) -> None:
        integration_type = PROVIDER_INTEGRATION_TYPES.get(provider)
        if integration_type is None:
            raise ValidationError(f"Provider '{provider.value}' is not configurable.")
        if provider == LLMProviderEnum.LOCAL:
            if not base_url:
                raise ValidationError("Ollama requires a base URL.", errors={"base_url": ["Required."]})
        elif not api_key:
            raise ValidationError("An API key is required.", errors={"api_key": ["Required."]})

        row = await self.integrations.get_org_level(organization_id, integration_type)
        fields = {
            "access_token_encrypted": encrypt_secret(api_key) if api_key else None,
            "config": {"base_url": base_url} if base_url else None,
            "is_active": True,
        }
        if row is None:
            await self.integrations.create(
                organization_id=organization_id,
                created_by=actor.id,
                integration_type=integration_type,
                name=f"{provider.value} API credentials",
                **fields,
            )
        else:
            await self.integrations.update(row, fields, updated_by=actor.id)

        # Log the change, never the key value.
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_settings",
            changes={"provider": provider.value, "action": "key_set"},
        )
        await self.db.commit()

    async def remove_provider_key(
        self, *, organization_id: uuid.UUID, provider: LLMProviderEnum, actor: User
    ) -> None:
        integration_type = PROVIDER_INTEGRATION_TYPES.get(provider)
        row = (
            await self.integrations.get_org_level(organization_id, integration_type)
            if integration_type
            else None
        )
        if row is None:
            raise NotFoundError("No credentials stored for this provider.")
        await self.integrations.delete(row)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="ai_settings",
            changes={"provider": provider.value, "action": "key_removed"},
        )
        await self.db.commit()
