"""Email Template CRUD (Campaigns -> Email Templates). Templates are only
ever created as a side effect of approving an AI-generated email variant
(`save_as_template=True` on POST /ai/outputs/{id}/approve-email) — there is
no manual "create template" endpoint, matching the module's list of routes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.exceptions.errors import NotFoundError
from app.models.identity.models import User
from app.repositories.email_template_repository import EmailTemplateRepository
from app.schemas.common import ApiResponse
from app.schemas.email_generation import EmailTemplateResponse, EmailTemplateUpdateRequest
from app.schemas.email_serializers import serialize_email_template

router = APIRouter(prefix="/email-templates", tags=["email-templates"])


async def _require_template(template_id: uuid.UUID, organization_id: uuid.UUID, db: AsyncSession):
    template = await EmailTemplateRepository(db).get_by_id(template_id, organization_id)
    if template is None:
        raise NotFoundError("Email template not found.")
    return template


@router.get("", response_model=ApiResponse[list[EmailTemplateResponse]])
async def list_email_templates(
    search: str | None = Query(default=None, max_length=255),
    template_type: list[str] | None = Query(default=None),
    tone: list[str] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: Literal["created_at"] = Query(default="created_at"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[EmailTemplateResponse]]:
    templates, total = await EmailTemplateRepository(db).list_for_organization(
        user.organization_id, search=search, template_type=template_type, tone=tone,
        is_active=is_active, page=page, page_size=page_size,
    )
    return ApiResponse(
        data=[serialize_email_template(t) for t in templates],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{template_id}", response_model=ApiResponse[EmailTemplateResponse])
async def get_email_template(
    template_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailTemplateResponse]:
    template = await _require_template(template_id, user.organization_id, db)
    return ApiResponse(data=serialize_email_template(template))


@router.patch("/{template_id}", response_model=ApiResponse[EmailTemplateResponse])
async def update_email_template(
    template_id: uuid.UUID,
    payload: EmailTemplateUpdateRequest,
    user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailTemplateResponse]:
    repo = EmailTemplateRepository(db)
    template = await _require_template(template_id, user.organization_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        changes["version"] = template.version + 1
        template = await repo.update(template, changes, updated_by=user.id)
        await db.commit()
    return ApiResponse(data=serialize_email_template(template), message="Email template updated.")


@router.delete("/{template_id}", response_model=ApiResponse[None], status_code=status.HTTP_200_OK)
async def delete_email_template(
    template_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = EmailTemplateRepository(db)
    template = await _require_template(template_id, user.organization_id, db)
    await repo.soft_delete(template)
    await db.commit()
    return ApiResponse(message="Email template deleted.")
