import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.crm.models import Note
from app.models.enums import ActivityTypeEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.note_repository import NoteRepository


class NoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notes = NoteRepository(db)
        self.activities = ActivityRepository(db)

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Note]:
        return await self.notes.list_for_lead(lead_id)

    async def create(
        self, *, organization_id: uuid.UUID, lead_id: uuid.UUID, content: str, is_pinned: bool, actor: User
    ) -> Note:
        note = await self.notes.create(
            organization_id=organization_id, lead_id=lead_id, author_id=actor.id,
            content=content, is_pinned=is_pinned,
        )
        await self.activities.record(
            organization_id=organization_id, lead_id=lead_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.NOTE_ADDED,
            summary=f"Note added by {actor.full_name}",
            entity_type="note", entity_id=note.id,
        )
        await self.db.commit()
        return await self.notes.get_by_id(note.id, lead_id)  # type: ignore[return-value]

    async def update(
        self, lead_id: uuid.UUID, note_id: uuid.UUID, *,
        content: str | None, is_pinned: bool | None, actor: User,
    ) -> Note:
        note = await self.notes.get_by_id(note_id, lead_id)
        if note is None:
            raise NotFoundError("Note not found.")
        note = await self.notes.update(note, content=content, is_pinned=is_pinned, updated_by=actor.id)
        await self.activities.record(
            organization_id=note.organization_id, lead_id=lead_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.NOTE_UPDATED,
            summary=f"Note updated by {actor.full_name}",
            entity_type="note", entity_id=note.id,
        )
        await self.db.commit()
        return await self.notes.get_by_id(note.id, lead_id)  # type: ignore[return-value]

    async def delete(self, lead_id: uuid.UUID, note_id: uuid.UUID, *, actor: User) -> None:
        note = await self.notes.get_by_id(note_id, lead_id)
        if note is None:
            raise NotFoundError("Note not found.")
        organization_id = note.organization_id
        await self.notes.delete(note)
        await self.activities.record(
            organization_id=organization_id, lead_id=lead_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.NOTE_DELETED,
            summary=f"Note deleted by {actor.full_name}",
        )
        await self.db.commit()
