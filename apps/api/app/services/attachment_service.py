import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.crm.models import Attachment
from app.models.enums import ActivityTypeEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.attachment_repository import AttachmentRepository
from app.services.storage_service import StorageService


class AttachmentService:
    """Shared between the Lead and Company modules — Attachment is a
    polymorphic table anchored by exactly one of `lead_id`/`company_id`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.attachments = AttachmentRepository(db)
        self.activities = ActivityRepository(db)
        self.storage = StorageService()

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Attachment]:
        return await self.attachments.list_for_lead(lead_id)

    async def list_for_company(self, company_id: uuid.UUID) -> list[Attachment]:
        return await self.attachments.list_for_company(company_id)

    async def upload(
        self, *, organization_id: uuid.UUID, file: UploadFile, actor: User,
        lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None,
    ) -> Attachment:
        if lead_id is not None:
            file_key, _public_url, file_size = await self.storage.save_lead_attachment(
                organization_id, lead_id, file
            )
        elif company_id is not None:
            file_key, _public_url, file_size = await self.storage.save_company_attachment(
                organization_id, company_id, file
            )
        else:
            raise ValidationError("An attachment must belong to a lead or a company.")

        attachment = await self.attachments.create(
            organization_id=organization_id, lead_id=lead_id, company_id=company_id, uploaded_by=actor.id,
            filename=file.filename or "attachment", file_key=file_key,
            file_size=file_size, mime_type=file.content_type,
        )
        await self.activities.record(
            organization_id=organization_id, lead_id=lead_id, company_id=company_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.ATTACHMENT_UPLOADED,
            summary=f"{attachment.filename} uploaded by {actor.full_name}",
            entity_type="attachment", entity_id=attachment.id,
        )
        await self.db.commit()
        return await self.attachments.get_by_id(attachment.id, lead_id=lead_id, company_id=company_id)  # type: ignore[return-value]

    async def delete(
        self, *, attachment_id: uuid.UUID, actor: User,
        lead_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None,
    ) -> None:
        attachment = await self.attachments.get_by_id(attachment_id, lead_id=lead_id, company_id=company_id)
        if attachment is None:
            raise NotFoundError("Attachment not found.")
        organization_id = attachment.organization_id
        filename = attachment.filename
        if lead_id is not None:
            self.storage.delete_lead_attachment(organization_id, lead_id, attachment.file_key)
        elif company_id is not None:
            self.storage.delete_company_attachment(organization_id, company_id, attachment.file_key)
        await self.attachments.delete(attachment)
        await self.activities.record(
            organization_id=organization_id, lead_id=lead_id, company_id=company_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.ATTACHMENT_DELETED,
            summary=f"{filename} deleted by {actor.full_name}",
        )
        await self.db.commit()
