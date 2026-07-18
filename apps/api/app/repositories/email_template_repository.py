import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaigns.models import EmailTemplate


class EmailTemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, template_id: uuid.UUID, organization_id: uuid.UUID) -> EmailTemplate | None:
        return await self.db.scalar(
            select(EmailTemplate)
            .execution_options(populate_existing=True)
            .where(
                EmailTemplate.id == template_id,
                EmailTemplate.organization_id == organization_id,
                EmailTemplate.deleted_at.is_(None),
            )
        )

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> EmailTemplate:
        template = EmailTemplate(
            organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update(
        self, template: EmailTemplate, changes: dict[str, Any], *, updated_by: uuid.UUID | None
    ) -> EmailTemplate:
        for field, value in changes.items():
            setattr(template, field, value)
        template.updated_by = updated_by
        await self.db.flush()
        return template

    async def soft_delete(self, template: EmailTemplate) -> None:
        template.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        search: str | None = None,
        template_type: list[str] | None = None,
        tone: list[str] | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[EmailTemplate], int]:
        conditions = [
            EmailTemplate.organization_id == organization_id,
            EmailTemplate.deleted_at.is_(None),
        ]
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(
                or_(func.lower(EmailTemplate.name).like(like), func.lower(EmailTemplate.subject).like(like))
            )
        if template_type:
            conditions.append(EmailTemplate.template_type.in_(template_type))
        if tone:
            conditions.append(EmailTemplate.tone.in_(tone))
        if is_active is not None:
            conditions.append(EmailTemplate.is_active == is_active)

        total = await self.db.scalar(
            select(func.count(EmailTemplate.id)).where(and_(*conditions))
        ) or 0
        result = await self.db.scalars(
            select(EmailTemplate)
            .where(and_(*conditions))
            .order_by(EmailTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total
