import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remaining_domains import DashboardWidget


class DashboardWidgetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, widget_id: uuid.UUID, organization_id: uuid.UUID) -> DashboardWidget | None:
        return await self.db.scalar(
            select(DashboardWidget).where(
                DashboardWidget.id == widget_id, DashboardWidget.organization_id == organization_id
            )
        )

    async def list_for_user(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> list[DashboardWidget]:
        """A user's dashboard is their own widgets (`user_id` matches) plus
        any org-default widgets (`user_id IS NULL`)."""
        result = await self.db.scalars(
            select(DashboardWidget)
            .where(
                DashboardWidget.organization_id == organization_id,
                or_(DashboardWidget.user_id == user_id, DashboardWidget.user_id.is_(None)),
            )
            .order_by(DashboardWidget.position_y, DashboardWidget.position_x)
        )
        return list(result)

    async def create(self, *, organization_id: uuid.UUID, user_id: uuid.UUID | None, **fields: Any) -> DashboardWidget:
        widget = DashboardWidget(organization_id=organization_id, user_id=user_id, **fields)
        self.db.add(widget)
        await self.db.flush()
        return widget

    async def update(self, widget: DashboardWidget, changes: dict[str, Any]) -> DashboardWidget:
        for field, value in changes.items():
            setattr(widget, field, value)
        await self.db.flush()
        return widget

    async def delete(self, widget: DashboardWidget) -> None:
        await self.db.delete(widget)
        await self.db.flush()
