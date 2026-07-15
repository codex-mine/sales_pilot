import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Organization

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
