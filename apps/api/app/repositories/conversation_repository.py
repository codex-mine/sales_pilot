import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.communication.models import Conversation


class ConversationRepository:
    """Email threads (Communication domain). `touch()` is the single place
    `message_count`/`last_message_at` are bumped — both the Email Sending
    module (an outgoing Email) and the Inbox module (an incoming Message)
    call it, instead of each incrementing the counters inline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, conversation_id: uuid.UUID, organization_id: uuid.UUID) -> Conversation | None:
        return await self.db.scalar(
            select(Conversation)
            .options(
                selectinload(Conversation.lead),
                selectinload(Conversation.messages),
                selectinload(Conversation.emails),
            )
            .where(Conversation.id == conversation_id, Conversation.organization_id == organization_id)
        )

    async def get_open_for_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> Conversation | None:
        return await self.db.scalar(
            select(Conversation).where(
                Conversation.organization_id == organization_id,
                Conversation.lead_id == lead_id,
                Conversation.is_active.is_(True),
            )
        )

    async def list_for_lead(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> list[Conversation]:
        result = await self.db.scalars(
            select(Conversation)
            .options(
                selectinload(Conversation.lead),
                selectinload(Conversation.messages),
                selectinload(Conversation.emails),
            )
            .where(Conversation.organization_id == organization_id, Conversation.lead_id == lead_id)
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        return list(result)

    async def create(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID, **fields: Any) -> Conversation:
        conversation = Conversation(organization_id=organization_id, lead_id=lead_id, **fields)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def touch(self, conversation: Conversation) -> Conversation:
        """Bumps `last_message_at`/`message_count` — called once per new
        Email or Message attached to this conversation, from either
        direction, so the two counters never drift from the messages that
        actually exist."""
        conversation.last_message_at = datetime.now(timezone.utc)
        conversation.message_count += 1
        await self.db.flush()
        return conversation

    async def list_inbox(
        self,
        organization_id: uuid.UUID,
        *,
        classifications: list[str] | None = None,
        unread_only: bool = False,
        owner_id: uuid.UUID | None = None,
        exclude_classifications: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Conversation], int]:
        """The unified inbox list query. Filters operate against each
        conversation's MOST RECENT inbound Message (classification, read
        state) — an older message's classification doesn't keep a thread
        pinned to a stale filter bucket. Threads with no inbound Message
        yet (outbound-only so far) never match a classification/unread
        filter, but always show up unfiltered."""
        from sqlalchemy import and_, func, or_

        from app.models.communication.models import Message
        from app.models.crm.models import Lead

        latest_per_conversation = (
            select(Message.conversation_id.label("conversation_id"), func.max(Message.received_at).label("received_at"))
            .group_by(Message.conversation_id)
            .subquery()
        )
        latest_message = (
            select(Message)
            .join(
                latest_per_conversation,
                and_(
                    Message.conversation_id == latest_per_conversation.c.conversation_id,
                    Message.received_at == latest_per_conversation.c.received_at,
                ),
            )
            .subquery()
        )

        conditions = [Conversation.organization_id == organization_id, Conversation.message_count > 0]
        if owner_id is not None:
            conditions.append(Lead.owner_id == owner_id)
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(or_(func.lower(Lead.full_name).like(like), func.lower(Conversation.subject).like(like)))
        if classifications:
            conditions.append(latest_message.c.reply_classification.in_(classifications))
        if exclude_classifications:
            conditions.append(
                or_(
                    latest_message.c.reply_classification.is_(None),
                    latest_message.c.reply_classification.notin_(exclude_classifications),
                )
            )
        if unread_only:
            conditions.append(latest_message.c.is_read.is_(False))

        base = (
            select(Conversation)
            .join(Lead, Lead.id == Conversation.lead_id)
            .outerjoin(latest_message, latest_message.c.conversation_id == Conversation.id)
            .where(and_(*conditions))
        )

        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.options(
                selectinload(Conversation.lead),
                selectinload(Conversation.messages),
                selectinload(Conversation.emails),
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total
