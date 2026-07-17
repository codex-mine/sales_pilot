import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm.models import Note


class NoteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(
        self, note_id: uuid.UUID, *, lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None
    ) -> Note | None:
        conditions = [Note.id == note_id]
        if lead_id is not None:
            conditions.append(Note.lead_id == lead_id)
        if company_id is not None:
            conditions.append(Note.company_id == company_id)
        return await self.db.scalar(
            select(Note)
            .options(selectinload(Note.author))
            .execution_options(populate_existing=True)
            .where(*conditions)
        )

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Note]:
        result = await self.db.scalars(
            select(Note)
            .options(selectinload(Note.author))
            .where(Note.lead_id == lead_id)
            .order_by(Note.is_pinned.desc(), Note.created_at.desc())
        )
        return list(result)

    async def list_for_company(self, company_id: uuid.UUID) -> list[Note]:
        result = await self.db.scalars(
            select(Note)
            .options(selectinload(Note.author))
            .where(Note.company_id == company_id)
            .order_by(Note.is_pinned.desc(), Note.created_at.desc())
        )
        return list(result)

    async def create(
        self, *, organization_id: uuid.UUID, author_id: uuid.UUID | None, content: str, is_pinned: bool,
        lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None,
    ) -> Note:
        note = Note(
            organization_id=organization_id, lead_id=lead_id, company_id=company_id, author_id=author_id,
            content=content, is_pinned=is_pinned, created_by=author_id, updated_by=author_id,
        )
        self.db.add(note)
        await self.db.flush()
        return note

    async def update(self, note: Note, *, content: str | None, is_pinned: bool | None, updated_by: uuid.UUID | None) -> Note:
        if content is not None:
            note.content = content
        if is_pinned is not None:
            note.is_pinned = is_pinned
        note.updated_by = updated_by
        await self.db.flush()
        return note

    async def delete(self, note: Note) -> None:
        await self.db.delete(note)
        await self.db.flush()
