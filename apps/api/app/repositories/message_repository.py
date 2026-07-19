import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication.models import Message


class MessageRepository:
    """Inbound replies (Communication domain) — see the model docstring for
    why these are kept separate from outgoing `Email` rows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, message_id: uuid.UUID, organization_id: uuid.UUID) -> Message | None:
        return await self.db.scalar(
            select(Message).where(Message.id == message_id, Message.organization_id == organization_id)
        )

    async def get_by_external_message_id(self, external_message_id: str) -> Message | None:
        """Idempotency check at the application level — the partial unique
        index on this column is the DB-level guarantee; this gives the
        ingestion service a clean early-return instead of relying solely on
        catching an IntegrityError."""
        return await self.db.scalar(
            select(Message).where(Message.external_message_id == external_message_id)
        )

    async def create(self, *, organization_id: uuid.UUID, conversation_id: uuid.UUID, lead_id: uuid.UUID, **fields: Any) -> Message:
        message = Message(organization_id=organization_id, conversation_id=conversation_id, lead_id=lead_id, **fields)
        self.db.add(message)
        await self.db.flush()
        return message

    async def update(self, message: Message, changes: dict[str, Any]) -> Message:
        for field, value in changes.items():
            setattr(message, field, value)
        await self.db.flush()
        return message

    async def list_for_conversation(self, conversation_id: uuid.UUID, organization_id: uuid.UUID) -> list[Message]:
        result = await self.db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.organization_id == organization_id)
            .order_by(Message.received_at)
        )
        return list(result)
