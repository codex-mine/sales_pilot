import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai.models import PromptTemplate, PromptVersion


class PromptRepository:
    """PromptTemplate metadata is editable; PromptVersion rows are immutable
    snapshots — editing prompt content always means inserting version N+1 and
    repointing `active_version_id`, never mutating an existing version."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Templates ────────────────────────────────────────────────────────────

    async def get_template_by_id(
        self, template_id: uuid.UUID, organization_id: uuid.UUID
    ) -> PromptTemplate | None:
        return await self.db.scalar(
            select(PromptTemplate)
            .options(selectinload(PromptTemplate.versions))
            .execution_options(populate_existing=True)
            .where(
                PromptTemplate.id == template_id,
                PromptTemplate.organization_id == organization_id,
                PromptTemplate.deleted_at.is_(None),
            )
        )

    async def get_template_by_name(
        self, organization_id: uuid.UUID, name: str
    ) -> PromptTemplate | None:
        return await self.db.scalar(
            select(PromptTemplate).where(
                PromptTemplate.organization_id == organization_id,
                PromptTemplate.name == name,
                PromptTemplate.deleted_at.is_(None),
            )
        )

    async def list_templates(self, organization_id: uuid.UUID) -> list[PromptTemplate]:
        rows = await self.db.scalars(
            select(PromptTemplate)
            .where(
                PromptTemplate.organization_id == organization_id,
                PromptTemplate.deleted_at.is_(None),
            )
            .order_by(PromptTemplate.name)
        )
        return list(rows)

    async def create_template(
        self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any
    ) -> PromptTemplate:
        template = PromptTemplate(
            organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self, template: PromptTemplate, changes: dict[str, Any], *, updated_by: uuid.UUID | None
    ) -> PromptTemplate:
        for f, v in changes.items():
            setattr(template, f, v)
        template.updated_by = updated_by
        await self.db.flush()
        return template

    # ─── Versions ─────────────────────────────────────────────────────────────

    async def get_version_by_id(
        self, version_id: uuid.UUID, organization_id: uuid.UUID
    ) -> PromptVersion | None:
        return await self.db.scalar(
            select(PromptVersion).where(
                PromptVersion.id == version_id,
                PromptVersion.organization_id == organization_id,
            )
        )

    async def list_versions(self, template_id: uuid.UUID) -> list[PromptVersion]:
        rows = await self.db.scalars(
            select(PromptVersion)
            .where(PromptVersion.template_id == template_id)
            .order_by(PromptVersion.version_number.desc())
        )
        return list(rows)

    async def next_version_number(self, template_id: uuid.UUID) -> int:
        current = await self.db.scalar(
            select(func.max(PromptVersion.version_number)).where(
                PromptVersion.template_id == template_id
            )
        )
        return (current or 0) + 1

    async def create_version(
        self,
        *,
        template_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID | None,
        **fields: Any,
    ) -> PromptVersion:
        version = PromptVersion(
            template_id=template_id,
            organization_id=organization_id,
            version_number=await self.next_version_number(template_id),
            created_by=created_by,
            updated_by=created_by,
            **fields,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_active_version(
        self, organization_id: uuid.UUID, template_name: str
    ) -> tuple[PromptTemplate, PromptVersion] | None:
        template = await self.get_template_by_name(organization_id, template_name)
        if template is None or template.active_version_id is None:
            return None
        version = await self.get_version_by_id(template.active_version_id, organization_id)
        if version is None:
            return None
        return template, version
