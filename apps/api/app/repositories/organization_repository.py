import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Organization, User

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    slug = _SLUG_INVALID_CHARS.sub("-", name.lower()).strip("-")
    return slug or "org"


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return await self.db.scalar(
            select(Organization).where(Organization.id == organization_id)
        )

    async def get_by_slug(self, slug: str) -> Organization | None:
        return await self.db.scalar(select(Organization).where(Organization.slug == slug))

    async def generate_unique_slug(self, name: str) -> str:
        base = slugify(name)
        slug = base
        suffix = 1
        while await self.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base}-{suffix}"
        return slug

    async def create(self, *, name: str, slug: str) -> Organization:
        organization = Organization(name=name, slug=slug)
        self.db.add(organization)
        await self.db.flush()
        return organization

    async def count_members(self, organization_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(User.id)).where(
                User.organization_id == organization_id, User.deleted_at.is_(None)
            )
        ) or 0

    async def update(self, organization: Organization, changes: dict[str, Any]) -> Organization:
        for field, value in changes.items():
            setattr(organization, field, value)
        await self.db.flush()
        return organization

    async def soft_delete(self, organization: Organization) -> Organization:
        organization.deleted_at = datetime.now(timezone.utc)
        organization.is_active = False
        await self.db.flush()
        return organization
