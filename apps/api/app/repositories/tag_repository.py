import uuid

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm.models import Company, CompanyTag, Lead, LeadTag, Tag


class TagRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Tag]:
        result = await self.db.scalars(
            select(Tag).where(Tag.organization_id == organization_id).order_by(Tag.name)
        )
        return list(result)

    async def get_or_create_many(self, organization_id: uuid.UUID, names: list[str]) -> list[Tag]:
        """Case-insensitive get-or-create, de-duplicating the input list itself too."""
        normalized = list({name.strip() for name in names if name.strip()})
        if not normalized:
            return []

        existing = await self.db.scalars(
            select(Tag).where(Tag.organization_id == organization_id, Tag.name.in_(normalized))
        )
        existing_tags = list(existing)
        existing_names_lower = {tag.name.lower() for tag in existing_tags}

        new_tags = [
            Tag(organization_id=organization_id, name=name)
            for name in normalized
            if name.lower() not in existing_names_lower
        ]
        if new_tags:
            self.db.add_all(new_tags)
            await self.db.flush()

        return existing_tags + new_tags

    async def set_tags_for_lead(self, lead: Lead, tags: list[Tag]) -> None:
        """Replaces the lead's full tag set (used by the update/create lead flows)."""
        await self.db.execute(delete(LeadTag).where(LeadTag.lead_id == lead.id))
        if tags:
            await self.db.execute(
                insert(LeadTag), [{"lead_id": lead.id, "tag_id": tag.id} for tag in tags]
            )
        await self.db.flush()

    async def add_tags_to_leads(self, lead_ids: list[uuid.UUID], tags: list[Tag]) -> None:
        """Additive — used by the bulk 'add tags' action; never removes existing tags."""
        if not lead_ids or not tags:
            return
        existing = await self.db.execute(
            select(LeadTag.lead_id, LeadTag.tag_id).where(LeadTag.lead_id.in_(lead_ids))
        )
        existing_pairs = set(existing.all())
        rows = [
            {"lead_id": lead_id, "tag_id": tag.id}
            for lead_id in lead_ids
            for tag in tags
            if (lead_id, tag.id) not in existing_pairs
        ]
        if rows:
            await self.db.execute(insert(LeadTag), rows)
            await self.db.flush()

    async def remove_tags_from_leads(self, lead_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]) -> None:
        if not lead_ids or not tag_ids:
            return
        await self.db.execute(
            delete(LeadTag).where(LeadTag.lead_id.in_(lead_ids), LeadTag.tag_id.in_(tag_ids))
        )
        await self.db.flush()

    # ─── Company tags (same Tag pool, separate M:M junction) ───────────────────

    async def set_tags_for_company(self, company: Company, tags: list[Tag]) -> None:
        """Replaces the company's full tag set (used by the update/create company flows)."""
        await self.db.execute(delete(CompanyTag).where(CompanyTag.company_id == company.id))
        if tags:
            await self.db.execute(
                insert(CompanyTag), [{"company_id": company.id, "tag_id": tag.id} for tag in tags]
            )
        await self.db.flush()

    async def add_tags_to_companies(self, company_ids: list[uuid.UUID], tags: list[Tag]) -> None:
        """Additive — used by the bulk 'add tags' action; never removes existing tags."""
        if not company_ids or not tags:
            return
        existing = await self.db.execute(
            select(CompanyTag.company_id, CompanyTag.tag_id).where(CompanyTag.company_id.in_(company_ids))
        )
        existing_pairs = set(existing.all())
        rows = [
            {"company_id": company_id, "tag_id": tag.id}
            for company_id in company_ids
            for tag in tags
            if (company_id, tag.id) not in existing_pairs
        ]
        if rows:
            await self.db.execute(insert(CompanyTag), rows)
            await self.db.flush()

    async def remove_tags_from_companies(self, company_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]) -> None:
        if not company_ids or not tag_ids:
            return
        await self.db.execute(
            delete(CompanyTag).where(CompanyTag.company_id.in_(company_ids), CompanyTag.tag_id.in_(tag_ids))
        )
        await self.db.flush()
