import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remaining_domains import Integration


class IntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_org_level(
        self, organization_id: uuid.UUID, integration_type: str
    ) -> Integration | None:
        """Org-level integrations have user_id NULL (the unique constraint
        allows multiple NULLs, so code — not the DB — enforces one row per
        org+type here by always fetching-then-updating)."""
        return await self.db.scalar(
            select(Integration).where(
                Integration.organization_id == organization_id,
                Integration.user_id.is_(None),
                Integration.integration_type == integration_type,
                Integration.deleted_at.is_(None),
            )
        )

    async def get_user_level(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, integration_type: str
    ) -> Integration | None:
        """User-level integrations (calendar, personal email) — one row per
        (org, user, type), enforced by the model's own unique constraint since
        `user_id` is set here (unlike `get_org_level`'s NULL)."""
        return await self.db.scalar(
            select(Integration).where(
                Integration.organization_id == organization_id,
                Integration.user_id == user_id,
                Integration.integration_type == integration_type,
                Integration.deleted_at.is_(None),
            )
        )

    async def list_org_level(self, organization_id: uuid.UUID) -> list[Integration]:
        rows = await self.db.scalars(
            select(Integration).where(
                Integration.organization_id == organization_id,
                Integration.user_id.is_(None),
                Integration.deleted_at.is_(None),
            )
        )
        return list(rows)

    async def list_org_level_by_type(self, organization_id: uuid.UUID, integration_type: str) -> list[Integration]:
        """Same as `list_org_level` but filtered to one type — used for
        multi-mailbox SMTP sender management, where an org now genuinely has
        more than one `integration_type="smtp"` row (unlike `get_org_level`'s
        single-row convention)."""
        rows = await self.db.scalars(
            select(Integration).where(
                Integration.organization_id == organization_id,
                Integration.user_id.is_(None),
                Integration.integration_type == integration_type,
                Integration.deleted_at.is_(None),
            ).order_by(Integration.created_at)
        )
        return list(rows)

    async def get_by_id(self, integration_id: uuid.UUID, organization_id: uuid.UUID) -> Integration | None:
        return await self.db.scalar(
            select(Integration).where(
                Integration.id == integration_id, Integration.organization_id == organization_id,
                Integration.deleted_at.is_(None),
            )
        )

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> Integration:
        integration = Integration(
            organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def update(
        self, integration: Integration, changes: dict[str, Any], *, updated_by: uuid.UUID | None
    ) -> Integration:
        for f, v in changes.items():
            setattr(integration, f, v)
        integration.updated_by = updated_by
        await self.db.flush()
        return integration

    async def delete(self, integration: Integration) -> None:
        """Hard delete — an Integration row holds only credentials/config, and
        a removed API key should not linger encrypted in a soft-deleted row."""
        await self.db.delete(integration)
        await self.db.flush()
