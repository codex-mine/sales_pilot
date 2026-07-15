import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditActionEnum
from app.models.remaining_domains import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        organization_id: uuid.UUID | None,
        actor_id: uuid.UUID | None,
        actor_email: str | None,
        action: AuditActionEnum,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        changes: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
