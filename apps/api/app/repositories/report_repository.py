import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remaining_domains import Report


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, report_id: uuid.UUID, organization_id: uuid.UUID) -> Report | None:
        return await self.db.scalar(
            select(Report).where(
                Report.id == report_id, Report.organization_id == organization_id, Report.deleted_at.is_(None)
            )
        )

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, page: int = 1, page_size: int = 25
    ) -> tuple[list[Report], int]:
        base = select(Report).where(Report.organization_id == organization_id, Report.deleted_at.is_(None))
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result), total

    async def list_due_scheduled(self, organization_id: uuid.UUID | None = None) -> list[Report]:
        """Every non-deleted scheduled report — the delivery task itself
        decides "is this actually due" (see `_is_due` in
        `app/workers/analytics_tasks.py`) since due-ness depends on
        `schedule_cron`'s daily/weekly/monthly cadence, not something
        expressible as a single SQL predicate here."""
        conditions = [Report.is_scheduled.is_(True), Report.deleted_at.is_(None)]
        if organization_id is not None:
            conditions.append(Report.organization_id == organization_id)
        result = await self.db.scalars(select(Report).where(*conditions))
        return list(result)

    async def create(self, *, organization_id: uuid.UUID, created_by: uuid.UUID | None, **fields: Any) -> Report:
        report = Report(organization_id=organization_id, created_by=created_by, updated_by=created_by, **fields)
        self.db.add(report)
        await self.db.flush()
        return report

    async def update(self, report: Report, changes: dict[str, Any], *, updated_by: uuid.UUID | None) -> Report:
        for field, value in changes.items():
            setattr(report, field, value)
        report.updated_by = updated_by
        await self.db.flush()
        return report

    async def record_run(self, report: Report) -> Report:
        report.last_run_at = datetime.now(timezone.utc)
        await self.db.flush()
        return report

    async def soft_delete(self, report: Report) -> None:
        report.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
