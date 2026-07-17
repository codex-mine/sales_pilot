import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm.models import Attachment


class AttachmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(
        self, attachment_id: uuid.UUID, *, lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None
    ) -> Attachment | None:
        conditions = [Attachment.id == attachment_id]
        if lead_id is not None:
            conditions.append(Attachment.lead_id == lead_id)
        if company_id is not None:
            conditions.append(Attachment.company_id == company_id)
        return await self.db.scalar(
            select(Attachment)
            .options(selectinload(Attachment.uploader))
            .execution_options(populate_existing=True)
            .where(*conditions)
        )

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Attachment]:
        result = await self.db.scalars(
            select(Attachment)
            .options(selectinload(Attachment.uploader))
            .where(Attachment.lead_id == lead_id)
            .order_by(Attachment.created_at.desc())
        )
        return list(result)

    async def list_for_company(self, company_id: uuid.UUID) -> list[Attachment]:
        result = await self.db.scalars(
            select(Attachment)
            .options(selectinload(Attachment.uploader))
            .where(Attachment.company_id == company_id)
            .order_by(Attachment.created_at.desc())
        )
        return list(result)

    async def create(
        self, *, organization_id: uuid.UUID, uploaded_by: uuid.UUID | None,
        filename: str, file_key: str, file_size: int | None, mime_type: str | None,
        lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None,
    ) -> Attachment:
        attachment = Attachment(
            organization_id=organization_id, lead_id=lead_id, company_id=company_id, uploaded_by=uploaded_by,
            filename=filename, file_key=file_key, file_size=file_size, mime_type=mime_type,
            created_by=uploaded_by, updated_by=uploaded_by,
        )
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def delete(self, attachment: Attachment) -> None:
        await self.db.delete(attachment)
        await self.db.flush()
