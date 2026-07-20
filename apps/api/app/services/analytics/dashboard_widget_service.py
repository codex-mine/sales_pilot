"""Per-user dashboard widget layout CRUD. Low-stakes personalization — no
Activity/AuditLog on reposition (see module 12 prompt's audit-log guidance);
create/delete are still audit-logged since they change what data a user's
dashboard exposes, not just where it sits."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.models.remaining_domains import DashboardWidget
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.dashboard_widget_repository import DashboardWidgetRepository
from app.schemas.analytics import CreateDashboardWidgetRequest, UpdateDashboardWidgetRequest


class DashboardWidgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.widgets = DashboardWidgetRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_widget(self, widget_id: uuid.UUID, organization_id: uuid.UUID) -> DashboardWidget:
        widget = await self.widgets.get_by_id(widget_id, organization_id)
        if widget is None:
            raise NotFoundError("Dashboard widget not found.")
        return widget

    async def list_for_user(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> list[DashboardWidget]:
        return await self.widgets.list_for_user(organization_id, user_id)

    async def create(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, *, payload: CreateDashboardWidgetRequest, actor: User
    ) -> DashboardWidget:
        widget = await self.widgets.create(organization_id=organization_id, user_id=user_id, **payload.model_dump())
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="dashboard_widget", resource_id=widget.id,
            changes={"event": "dashboard_widget_added", "widget_type": payload.widget_type},
        )
        await self.db.commit()
        # Re-fetch: `updated_at`'s `onupdate=func.now()` is server-computed,
        # so the in-memory value is stale until an awaited re-read.
        return await self.require_widget(widget.id, organization_id)

    async def update(
        self, widget: DashboardWidget, *, payload: UpdateDashboardWidgetRequest, actor: User
    ) -> DashboardWidget:
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return widget
        widget = await self.widgets.update(widget, changes)
        await self.db.commit()
        return await self.require_widget(widget.id, widget.organization_id)

    async def delete(self, widget: DashboardWidget, *, actor: User) -> None:
        await self.audit_log.record(
            organization_id=widget.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="dashboard_widget", resource_id=widget.id,
            changes={"event": "dashboard_widget_removed", "widget_type": widget.widget_type},
        )
        await self.widgets.delete(widget)
        await self.db.commit()
