import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm.models import Activity, Attachment, Lead, LeadTag, Note, Tag


class LeadRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> Lead | None:
        return await self.db.scalar(
            select(Lead)
            .options(selectinload(Lead.tags), selectinload(Lead.owner))
            # This is called both for a fresh read AND to re-fetch a lead
            # that was already loaded earlier in the same request (e.g.
            # `require_lead()` then `update()`) — without `populate_existing`,
            # SQLAlchemy trusts the identity map and skips reloading
            # relationships it thinks are already populated, so a just-changed
            # `owner_id` wouldn't be reflected in `lead.owner` on the re-fetch.
            .execution_options(populate_existing=True)
            .where(
                Lead.id == lead_id,
                Lead.organization_id == organization_id,
                Lead.deleted_at.is_(None),
            )
        )

    async def get_by_email(self, organization_id: uuid.UUID, email: str) -> Lead | None:
        return await self.db.scalar(
            select(Lead).where(
                Lead.organization_id == organization_id,
                func.lower(Lead.email) == email.lower(),
                Lead.deleted_at.is_(None),
            )
        )

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> Lead:
        lead = Lead(organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields)
        self.db.add(lead)
        await self.db.flush()
        return lead

    async def update(self, lead: Lead, changes: dict[str, Any], *, updated_by: uuid.UUID | None) -> Lead:
        for field, value in changes.items():
            setattr(lead, field, value)
        lead.updated_by = updated_by
        await self.db.flush()
        return lead

    async def soft_delete(self, lead: Lead) -> None:
        lead.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ─── Counts (used to hydrate notes_count / attachments_count / activities_count) ──

    async def counts_for_leads(
        self, lead_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict[str, int]]:
        """One grouped query per related table instead of N+1 per-lead counts."""
        if not lead_ids:
            return {}
        result: dict[uuid.UUID, dict[str, int]] = {
            lead_id: {"notes": 0, "attachments": 0, "activities": 0} for lead_id in lead_ids
        }
        for model, key in ((Note, "notes"), (Attachment, "attachments"), (Activity, "activities")):
            rows = await self.db.execute(
                select(model.lead_id, func.count(model.id))
                .where(model.lead_id.in_(lead_ids))
                .group_by(model.lead_id)
            )
            for lead_id, count in rows.all():
                result[lead_id][key] = count
        return result

    async def status_distribution(self, organization_id: uuid.UUID) -> dict[str, int]:
        """Live `Lead.status` GROUP BY for the module 12 dashboard's Pipeline
        Funnel widget. `Lead` is small and already indexed on
        (organization_id, status)-adjacent columns, so this is the "cheap even
        unaggregated" exception called out in ARCHITECTURE.md's Metric-first
        rule — reading live also means the funnel never lags a nightly batch,
        which matters most for the single most-checked dashboard widget."""
        rows = await self.db.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.organization_id == organization_id, Lead.deleted_at.is_(None))
            .group_by(Lead.status)
        )
        return {status: count for status, count in rows.all()}

    # ─── List / search / filter / sort / paginate ──────────────────────────────

    _SORT_COLUMNS = {
        "name": Lead.first_name,
        "company": Lead.company_name,
        "lead_score": Lead.lead_score,
        "status": Lead.status,
        "created_at": Lead.created_at,
        "updated_at": Lead.updated_at,
        "priority": Lead.priority,
    }

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        search: str | None = None,
        status: list[str] | None = None,
        source: list[str] | None = None,
        owner_ids: list[uuid.UUID] | None = None,
        tag_names: list[str] | None = None,
        country: str | None = None,
        industry: str | None = None,
        company: str | None = None,
        is_favorite: bool | None = None,
        is_archived: bool | None = None,
        lead_score_min: float | None = None,
        lead_score_max: float | None = None,
        priority_min: int | None = None,
        priority_max: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Lead], int]:
        conditions = [Lead.organization_id == organization_id, Lead.deleted_at.is_(None)]

        if search:
            like = f"%{search.strip().lower()}%"
            search_conditions = [
                func.lower(Lead.first_name).like(like),
                func.lower(Lead.last_name).like(like),
                func.lower(Lead.email).like(like),
                func.lower(Lead.phone).like(like),
                func.lower(Lead.company_name).like(like),
                func.lower(Lead.website).like(like),
                func.lower(Lead.job_title).like(like),
            ]
            note_match = select(Note.lead_id).where(func.lower(Note.content).like(like))
            tag_match = (
                select(LeadTag.lead_id)
                .join(Tag, Tag.id == LeadTag.tag_id)
                .where(func.lower(Tag.name).like(like))
            )
            conditions.append(
                or_(*search_conditions, Lead.id.in_(note_match), Lead.id.in_(tag_match))
            )

        if status:
            conditions.append(Lead.status.in_(status))
        if source:
            conditions.append(Lead.source.in_(source))
        if owner_ids:
            conditions.append(Lead.owner_id.in_(owner_ids))
        if country:
            conditions.append(func.lower(Lead.country) == country.lower())
        if industry:
            conditions.append(func.lower(Lead.industry) == industry.lower())
        if company:
            conditions.append(func.lower(Lead.company_name).like(f"%{company.lower()}%"))
        if is_favorite is not None:
            conditions.append(Lead.is_favorite == is_favorite)
        if is_archived is not None:
            conditions.append(Lead.is_archived == is_archived)
        else:
            # Archived leads are hidden from the default view unless explicitly requested.
            conditions.append(Lead.is_archived.is_(False))
        if lead_score_min is not None:
            conditions.append(Lead.lead_score >= lead_score_min)
        if lead_score_max is not None:
            conditions.append(Lead.lead_score <= lead_score_max)
        if priority_min is not None:
            conditions.append(Lead.priority >= priority_min)
        if priority_max is not None:
            conditions.append(Lead.priority <= priority_max)
        if created_from is not None:
            conditions.append(Lead.created_at >= created_from)
        if created_to is not None:
            conditions.append(Lead.created_at <= created_to)
        if updated_from is not None:
            conditions.append(Lead.updated_at >= updated_from)
        if updated_to is not None:
            conditions.append(Lead.updated_at <= updated_to)

        base_query = select(Lead).where(and_(*conditions))
        count_query = select(func.count(func.distinct(Lead.id))).where(and_(*conditions))

        if tag_names:
            tag_filter = (
                select(LeadTag.lead_id)
                .join(Tag, Tag.id == LeadTag.tag_id)
                .where(Tag.organization_id == organization_id, Tag.name.in_(tag_names))
            )
            base_query = base_query.where(Lead.id.in_(tag_filter))
            count_query = count_query.where(Lead.id.in_(tag_filter))

        total = await self.db.scalar(count_query) or 0

        sort_column = self._SORT_COLUMNS.get(sort_by, Lead.created_at)
        order = sort_column.desc() if sort_desc else sort_column.asc()
        base_query = (
            base_query.options(selectinload(Lead.tags), selectinload(Lead.owner))
            .order_by(order, Lead.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.scalars(base_query)
        return list(result.unique()), total

    async def get_many_by_ids(self, lead_ids: list[uuid.UUID], organization_id: uuid.UUID) -> list[Lead]:
        result = await self.db.scalars(
            select(Lead)
            .options(selectinload(Lead.tags), selectinload(Lead.owner))
            .where(
                Lead.id.in_(lead_ids),
                Lead.organization_id == organization_id,
                Lead.deleted_at.is_(None),
            )
        )
        return list(result.unique())
