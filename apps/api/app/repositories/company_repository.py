import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm.models import Activity, Attachment, Company, CompanyTag, Contact, Lead, Note, Tag


class CompanyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, company_id: uuid.UUID, organization_id: uuid.UUID) -> Company | None:
        return await self.db.scalar(
            select(Company)
            .options(selectinload(Company.tags), selectinload(Company.owner))
            # See LeadRepository.get_by_id for why `populate_existing` is
            # required here — without it, a re-fetch of an already-loaded
            # Company within the same request (e.g. update() re-fetching
            # after a just-changed owner_id) would keep the stale `owner`
            # relationship from the identity map.
            .execution_options(populate_existing=True)
            .where(
                Company.id == company_id,
                Company.organization_id == organization_id,
                Company.deleted_at.is_(None),
            )
        )

    async def get_by_domain(self, organization_id: uuid.UUID, domain: str) -> Company | None:
        return await self.db.scalar(
            select(Company).where(
                Company.organization_id == organization_id,
                Company.domain == domain,
                Company.deleted_at.is_(None),
            )
        )

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> Company:
        company = Company(organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields)
        self.db.add(company)
        await self.db.flush()
        return company

    async def update(self, company: Company, changes: dict[str, Any], *, updated_by: uuid.UUID | None) -> Company:
        for field, value in changes.items():
            setattr(company, field, value)
        company.updated_by = updated_by
        await self.db.flush()
        return company

    async def soft_delete(self, company: Company) -> None:
        company.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ─── Counts (notes_count / attachments_count / contact_count / lead_count) ─

    async def counts_for_companies(self, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        """One grouped query per related table instead of N+1 per-company counts."""
        if not company_ids:
            return {}
        result: dict[uuid.UUID, dict[str, int]] = {
            company_id: {"notes": 0, "attachments": 0, "contacts": 0, "leads": 0} for company_id in company_ids
        }
        for model, key in ((Note, "notes"), (Attachment, "attachments"), (Contact, "contacts"), (Lead, "leads")):
            column = model.company_id
            rows = await self.db.execute(
                select(column, func.count(model.id)).where(column.in_(company_ids)).group_by(column)
            )
            for company_id, count in rows.all():
                result[company_id][key] = count
        return result

    # ─── List / search / filter / sort / paginate ──────────────────────────────

    _SORT_COLUMNS = {
        "name": Company.name,
        "industry": Company.industry,
        "status": Company.status,
        "employee_count": Company.employee_count,
        "annual_revenue": Company.annual_revenue,
        "created_at": Company.created_at,
        "updated_at": Company.updated_at,
    }

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        search: str | None = None,
        status: list[str] | None = None,
        industry: list[str] | None = None,
        size_range: list[str] | None = None,
        owner_ids: list[uuid.UUID] | None = None,
        tag_names: list[str] | None = None,
        country: str | None = None,
        is_archived: bool | None = None,
        revenue_min: float | None = None,
        revenue_max: float | None = None,
        employee_count_min: int | None = None,
        employee_count_max: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Company], int]:
        conditions = [Company.organization_id == organization_id, Company.deleted_at.is_(None)]

        if search:
            like = f"%{search.strip().lower()}%"
            search_conditions = [
                func.lower(Company.name).like(like),
                func.lower(Company.legal_name).like(like),
                func.lower(Company.website).like(like),
                func.lower(Company.domain).like(like),
                func.lower(Company.email).like(like),
                func.lower(Company.industry).like(like),
            ]
            note_match = select(Note.company_id).where(func.lower(Note.content).like(like))
            tag_match = (
                select(CompanyTag.company_id)
                .join(Tag, Tag.id == CompanyTag.tag_id)
                .where(func.lower(Tag.name).like(like))
            )
            conditions.append(
                or_(*search_conditions, Company.id.in_(note_match), Company.id.in_(tag_match))
            )

        if status:
            conditions.append(Company.status.in_(status))
        if industry:
            conditions.append(Company.industry.in_(industry))
        if size_range:
            conditions.append(Company.size_range.in_(size_range))
        if owner_ids:
            conditions.append(Company.owner_id.in_(owner_ids))
        if country:
            conditions.append(func.lower(Company.country) == country.lower())
        if is_archived is not None:
            if is_archived:
                conditions.append(Company.archived_at.isnot(None))
            else:
                conditions.append(Company.archived_at.is_(None))
        else:
            # Archived companies are hidden from the default view unless explicitly requested.
            conditions.append(Company.archived_at.is_(None))
        if revenue_min is not None:
            conditions.append(Company.annual_revenue >= revenue_min)
        if revenue_max is not None:
            conditions.append(Company.annual_revenue <= revenue_max)
        if employee_count_min is not None:
            conditions.append(Company.employee_count >= employee_count_min)
        if employee_count_max is not None:
            conditions.append(Company.employee_count <= employee_count_max)
        if created_from is not None:
            conditions.append(Company.created_at >= created_from)
        if created_to is not None:
            conditions.append(Company.created_at <= created_to)
        if updated_from is not None:
            conditions.append(Company.updated_at >= updated_from)
        if updated_to is not None:
            conditions.append(Company.updated_at <= updated_to)

        base_query = select(Company).where(and_(*conditions))
        count_query = select(func.count(func.distinct(Company.id))).where(and_(*conditions))

        if tag_names:
            tag_filter = (
                select(CompanyTag.company_id)
                .join(Tag, Tag.id == CompanyTag.tag_id)
                .where(Tag.organization_id == organization_id, Tag.name.in_(tag_names))
            )
            base_query = base_query.where(Company.id.in_(tag_filter))
            count_query = count_query.where(Company.id.in_(tag_filter))

        total = await self.db.scalar(count_query) or 0

        sort_column = self._SORT_COLUMNS.get(sort_by, Company.created_at)
        order = sort_column.desc() if sort_desc else sort_column.asc()
        base_query = (
            base_query.options(selectinload(Company.tags), selectinload(Company.owner))
            .order_by(order, Company.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.scalars(base_query)
        return list(result.unique()), total

    async def get_many_by_ids(self, company_ids: list[uuid.UUID], organization_id: uuid.UUID) -> list[Company]:
        result = await self.db.scalars(
            select(Company)
            .options(selectinload(Company.tags), selectinload(Company.owner))
            .where(
                Company.id.in_(company_ids),
                Company.organization_id == organization_id,
                Company.deleted_at.is_(None),
            )
        )
        return list(result.unique())

    # ─── Employees (read-only Contact list for the Company > Employees tab) ────

    async def list_employees(
        self,
        company_id: uuid.UUID,
        *,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Contact], int]:
        conditions = [Contact.company_id == company_id, Contact.deleted_at.is_(None)]

        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(Contact.first_name).like(like),
                    func.lower(Contact.last_name).like(like),
                    func.lower(Contact.email).like(like),
                    func.lower(Contact.job_title).like(like),
                    func.lower(Contact.department).like(like),
                )
            )
        if status:
            conditions.append(Contact.status == status)

        total = await self.db.scalar(
            select(func.count(Contact.id)).where(and_(*conditions))
        ) or 0
        result = await self.db.scalars(
            select(Contact)
            .options(selectinload(Contact.leads))
            .where(and_(*conditions))
            .order_by(Contact.first_name, Contact.last_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.unique()), total
