import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.common import ApiResponse
from app.schemas.companies import (
    BulkActionError,
    BulkActionResponse,
    BulkCompanyActionRequest,
    CompanyActivityResponse,
    CompanyAttachmentResponse,
    CompanyCreateRequest,
    CompanyEmployeeResponse,
    CompanyNoteResponse,
    CompanyResponse,
    CompanyTagResponse,
    CompanyUpdateRequest,
)
from app.schemas.leads import NoteCreateRequest, NoteUpdateRequest
from app.schemas.company_serializers import (
    serialize_company,
    serialize_company_activity,
    serialize_company_attachment,
    serialize_company_note,
    serialize_company_tag,
    serialize_employee,
)
from app.services.attachment_service import AttachmentService
from app.services.company_service import CompanyService
from app.services.note_service import NoteService

router = APIRouter(prefix="/companies", tags=["companies"])


async def _company_response(
    company_id: uuid.UUID, organization_id: uuid.UUID, db: AsyncSession
) -> CompanyResponse:
    company = await CompanyService(db).require_company(company_id, organization_id)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return serialize_company(company, counts=counts)


# NOTE ON ROUTE ORDER: static-string routes (/tags, /export, /bulk) must be
# declared before the `/{company_id}` family below, or a request like
# "GET /companies/export" would be misrouted into `get_company` and fail
# UUID parsing — see the Lead/Organization modules for the same lesson.

# ─── List / create ──────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[list[CompanyResponse]])
async def list_companies(
    search: str | None = Query(default=None, max_length=255),
    status_filter: list[str] | None = Query(default=None, alias="status"),
    industry: list[str] | None = Query(default=None),
    size_range: list[str] | None = Query(default=None),
    owner_id: list[uuid.UUID] | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    country: str | None = Query(default=None),
    archived: bool | None = Query(default=None),
    revenue_min: float | None = Query(default=None),
    revenue_max: float | None = Query(default=None),
    employee_count_min: int | None = Query(default=None),
    employee_count_max: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    updated_from: datetime | None = Query(default=None),
    updated_to: datetime | None = Query(default=None),
    sort_by: Literal[
        "name", "industry", "status", "employee_count", "annual_revenue", "created_at", "updated_at",
    ] = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyResponse]]:
    repo = CompanyRepository(db)
    companies, total = await repo.list_for_organization(
        user.organization_id,
        search=search,
        status=status_filter,
        industry=industry,
        size_range=size_range,
        owner_ids=owner_id,
        tag_names=tag,
        country=country,
        is_archived=archived,
        revenue_min=revenue_min,
        revenue_max=revenue_max,
        employee_count_min=employee_count_min,
        employee_count_max=employee_count_max,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        sort_by=sort_by,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size,
    )
    counts = await repo.counts_for_companies([company.id for company in companies])
    return ApiResponse(
        data=[serialize_company(c, counts=counts.get(c.id, {})) for c in companies],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post(
    "", response_model=ApiResponse[CompanyResponse], status_code=status.HTTP_201_CREATED
)
async def create_company(
    payload: CompanyCreateRequest,
    user: User = Depends(require_permission("companies", "create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    company = await CompanyService(db).create(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Company created.")


# ─── Tags (read-only helper, mirrors /leads/tags — same org-scoped Tag pool) ────


@router.get("/tags", response_model=ApiResponse[list[CompanyTagResponse]])
async def list_company_tags(
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyTagResponse]]:
    tags = await TagRepository(db).list_for_organization(user.organization_id)
    return ApiResponse(data=[serialize_company_tag(tag) for tag in tags])


# ─── CSV export ─────────────────────────────────────────────────────────────────


@router.get("/export")
async def export_companies(
    company_ids: list[uuid.UUID] | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    status_filter: list[str] | None = Query(default=None, alias="status"),
    industry: list[str] | None = Query(default=None),
    owner_id: list[uuid.UUID] | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    archived: bool | None = Query(default=None),
    user: User = Depends(require_permission("companies", "export")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    repo = CompanyRepository(db)
    if company_ids:
        companies = await repo.get_many_by_ids(company_ids, user.organization_id)
    else:
        companies, _total = await repo.list_for_organization(
            user.organization_id,
            search=search,
            status=status_filter,
            industry=industry,
            owner_ids=owner_id,
            tag_names=tag,
            is_archived=archived,
            page=1,
            page_size=10_000,
        )
    csv_text = await CompanyService(db).export_csv(companies=companies)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="companies.csv"'},
    )


# ─── Bulk actions ───────────────────────────────────────────────────────────────


@router.post("/bulk", response_model=ApiResponse[BulkActionResponse])
async def bulk_companies(
    payload: BulkCompanyActionRequest,
    user: User = Depends(require_permission("companies", "bulk")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkActionResponse]:
    requested, success, errors = await CompanyService(db).bulk_action(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    return ApiResponse(
        data=BulkActionResponse(
            action=payload.action,
            requested_count=requested,
            success_count=success,
            failed_count=len(errors),
            errors=[BulkActionError(company_id=str(cid), message=msg) for cid, msg in errors],
        ),
        message=f"{success} of {requested} companies updated.",
    )


# ─── Company CRUD by id ─────────────────────────────────────────────────────────


@router.get("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def get_company(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    return ApiResponse(data=await _company_response(company_id, user.organization_id, db))


@router.patch("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    user: User = Depends(require_permission("companies", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    company = await service.update(company, payload=payload, actor=user)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Company updated.")


@router.post("/{company_id}/archive", response_model=ApiResponse[CompanyResponse])
async def archive_company(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    company = await service.archive(company, actor=user)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Company archived.")


@router.post("/{company_id}/restore", response_model=ApiResponse[CompanyResponse])
async def restore_company(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    company = await service.restore(company, actor=user)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Company restored.")


@router.delete("/{company_id}", response_model=ApiResponse[None])
async def delete_company(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    await service.delete(company, actor=user)
    return ApiResponse(message="Company deleted.")


# ─── Logo ───────────────────────────────────────────────────────────────────────


@router.post("/{company_id}/logo", response_model=ApiResponse[CompanyResponse])
async def upload_company_logo(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("companies", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    company = await service.upload_logo(company, file=file, actor=user)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Logo updated.")


@router.delete("/{company_id}/logo", response_model=ApiResponse[CompanyResponse])
async def delete_company_logo(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.require_company(company_id, user.organization_id)
    company = await service.delete_logo(company, actor=user)
    counts = (await CompanyRepository(db).counts_for_companies([company.id])).get(company.id, {})
    return ApiResponse(data=serialize_company(company, counts=counts), message="Logo removed.")


# ─── Employees (read-only Contact view) ─────────────────────────────────────────


@router.get("/{company_id}/employees", response_model=ApiResponse[list[CompanyEmployeeResponse]])
async def list_company_employees(
    company_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyEmployeeResponse]]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    employees, total = await CompanyRepository(db).list_employees(
        company_id, search=search, status=status_filter, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_employee(e) for e in employees],
        meta={"page": page, "page_size": page_size, "total": total},
    )


# ─── Notes ──────────────────────────────────────────────────────────────────────


@router.get("/{company_id}/notes", response_model=ApiResponse[list[CompanyNoteResponse]])
async def list_company_notes(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyNoteResponse]]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    notes = await NoteService(db).list_for_company(company_id)
    return ApiResponse(data=[serialize_company_note(n) for n in notes])


@router.post(
    "/{company_id}/notes",
    response_model=ApiResponse[CompanyNoteResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_company_note(
    company_id: uuid.UUID,
    payload: NoteCreateRequest,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyNoteResponse]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    note = await NoteService(db).create(
        organization_id=user.organization_id,
        company_id=company_id,
        content=payload.content,
        is_pinned=payload.is_pinned,
        actor=user,
    )
    return ApiResponse(data=serialize_company_note(note), message="Note added.")


@router.patch("/{company_id}/notes/{note_id}", response_model=ApiResponse[CompanyNoteResponse])
async def update_company_note(
    company_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdateRequest,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyNoteResponse]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    note = await NoteService(db).update(
        note_id=note_id,
        company_id=company_id,
        content=payload.content,
        is_pinned=payload.is_pinned,
        actor=user,
    )
    return ApiResponse(data=serialize_company_note(note), message="Note updated.")


@router.delete("/{company_id}/notes/{note_id}", response_model=ApiResponse[None])
async def delete_company_note(
    company_id: uuid.UUID,
    note_id: uuid.UUID,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    await NoteService(db).delete(note_id=note_id, company_id=company_id, actor=user)
    return ApiResponse(message="Note deleted.")


# ─── Activities ─────────────────────────────────────────────────────────────────


@router.get("/{company_id}/activities", response_model=ApiResponse[list[CompanyActivityResponse]])
async def list_company_activities(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyActivityResponse]]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    activities, total = await ActivityRepository(db).list_for_company(
        company_id, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_company_activity(a) for a in activities],
        meta={"page": page, "page_size": page_size, "total": total},
    )


# ─── Attachments ────────────────────────────────────────────────────────────────


@router.post(
    "/{company_id}/attachments",
    response_model=ApiResponse[CompanyAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_company_attachment(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("attachments", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CompanyAttachmentResponse]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    attachment = await AttachmentService(db).upload(
        organization_id=user.organization_id, company_id=company_id, file=file, actor=user
    )
    return ApiResponse(data=serialize_company_attachment(attachment), message="Attachment uploaded.")


@router.get(
    "/{company_id}/attachments", response_model=ApiResponse[list[CompanyAttachmentResponse]]
)
async def list_company_attachments(
    company_id: uuid.UUID,
    user: User = Depends(require_permission("companies", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CompanyAttachmentResponse]]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    attachments = await AttachmentService(db).list_for_company(company_id)
    return ApiResponse(data=[serialize_company_attachment(a) for a in attachments])


@router.delete(
    "/{company_id}/attachments/{attachment_id}", response_model=ApiResponse[None]
)
async def delete_company_attachment(
    company_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(require_permission("attachments", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await CompanyService(db).require_company(company_id, user.organization_id)
    await AttachmentService(db).delete(attachment_id=attachment_id, company_id=company_id, actor=user)
    return ApiResponse(message="Attachment deleted.")
