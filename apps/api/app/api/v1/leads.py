import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.enums import EmailTemplateTypeEnum, EmailToneEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.ai import AIJobResponse
from app.schemas.ai_serializers import serialize_job
from app.schemas.common import ApiResponse
from app.schemas.email_generation import (
    BulkEmailGenerationResponse,
    BulkLeadEmailGenerationRequest,
    EmailResponse,
    GenerateEmailRequest,
    RegenerateEmailRequest,
)
from app.schemas.email_sending import ScheduleEmailRequest
from app.schemas.email_serializers import serialize_email
from app.schemas.lead_serializers import (
    serialize_activity,
    serialize_attachment,
    serialize_lead,
    serialize_note,
    serialize_tag,
)
from app.schemas.leads import (
    ActivityResponse,
    AttachmentResponse,
    BulkActionError,
    BulkActionResponse,
    BulkLeadActionRequest,
    ImportPreviewResponse,
    ImportResultResponse,
    LeadCreateRequest,
    LeadResponse,
    LeadUpdateRequest,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest,
    TagResponse,
)
from app.schemas.research import (
    BulkLeadResearchRequest,
    BulkResearchResponse,
    LeadResearchStatusResponse,
    ProspectAnalysisResponse,
)
from app.schemas.research_serializers import serialize_prospect_analysis
from app.services.ai.email_generation_service import EmailGenerationService
from app.services.ai.prospect_analysis_service import ProspectAnalysisService
from app.services.attachment_service import AttachmentService
from app.services.email.email_sending_service import EmailSendingService
from app.services.lead_import_export_service import LeadImportExportService
from app.services.lead_service import LeadService
from app.services.note_service import NoteService

router = APIRouter(prefix="/leads", tags=["leads"])


async def _lead_response(
    lead_id: uuid.UUID, organization_id: uuid.UUID, db: AsyncSession
) -> LeadResponse:
    lead = await LeadService(db).require_lead(lead_id, organization_id)
    counts = (await LeadRepository(db).counts_for_leads([lead.id])).get(lead.id, {})
    return serialize_lead(lead, counts=counts)


# NOTE ON ROUTE ORDER: static-string routes (/import, /export, /bulk, /tags)
# must be declared before the `/{lead_id}` family below, or a request like
# "GET /leads/export" would be misrouted into `get_lead` and fail UUID
# parsing — see the Organization module's routes for the same lesson.

# ─── List / create ──────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[list[LeadResponse]])
async def list_leads(
    search: str | None = Query(default=None, max_length=255),
    status_filter: list[str] | None = Query(default=None, alias="status"),
    source: list[str] | None = Query(default=None),
    owner_id: list[uuid.UUID] | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    country: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    company: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    archived: bool | None = Query(default=None),
    lead_score_min: float | None = Query(default=None),
    lead_score_max: float | None = Query(default=None),
    priority_min: int | None = Query(default=None),
    priority_max: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    updated_from: datetime | None = Query(default=None),
    updated_to: datetime | None = Query(default=None),
    sort_by: Literal[
        "name",
        "company",
        "lead_score",
        "status",
        "created_at",
        "updated_at",
        "priority",
    ] = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[LeadResponse]]:
    repo = LeadRepository(db)
    leads, total = await repo.list_for_organization(
        user.organization_id,
        search=search,
        status=status_filter,
        source=source,
        owner_ids=owner_id,
        tag_names=tag,
        country=country,
        industry=industry,
        company=company,
        is_favorite=favorite,
        is_archived=archived,
        lead_score_min=lead_score_min,
        lead_score_max=lead_score_max,
        priority_min=priority_min,
        priority_max=priority_max,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        sort_by=sort_by,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size,
    )
    counts = await repo.counts_for_leads([lead.id for lead in leads])
    return ApiResponse(
        data=[serialize_lead(lead, counts=counts.get(lead.id, {})) for lead in leads],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post(
    "", response_model=ApiResponse[LeadResponse], status_code=status.HTTP_201_CREATED
)
async def create_lead(
    payload: LeadCreateRequest,
    user: User = Depends(require_permission("leads", "create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LeadResponse]:
    lead = await LeadService(db).create(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    counts = (await LeadRepository(db).counts_for_leads([lead.id])).get(lead.id, {})
    return ApiResponse(
        data=serialize_lead(lead, counts=counts), message="Lead created."
    )


# ─── Tags (read-only helper, mirrors /organizations/roles) ─────────────────────


@router.get("/tags", response_model=ApiResponse[list[TagResponse]])
async def list_tags(
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[TagResponse]]:
    tags = await TagRepository(db).list_for_organization(user.organization_id)
    return ApiResponse(data=[serialize_tag(tag) for tag in tags])


# ─── CSV import ─────────────────────────────────────────────────────────────────


@router.post(
    "/import", response_model=ApiResponse[ImportPreviewResponse | ImportResultResponse]
)
async def import_leads(
    file: UploadFile = File(...),
    mode: Literal["preview", "commit"] = Form(...),
    mapping: str | None = Form(default=None),
    user: User = Depends(require_permission("leads", "import")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportPreviewResponse | ImportResultResponse]:
    service = LeadImportExportService(db)
    if mode == "preview":
        preview = await service.preview(file)
        return ApiResponse(data=preview)

    if not mapping:
        raise ValidationError(
            "Column mapping is required to commit an import.",
            errors={"mapping": ["Required."]},
        )
    try:
        parsed_mapping: dict[str, str] = json.loads(mapping)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "Mapping must be valid JSON.", errors={"mapping": ["Invalid JSON."]}
        ) from exc

    result = await service.commit(
        organization_id=user.organization_id,
        file=file,
        mapping=parsed_mapping,
        actor=user,
    )
    return ApiResponse(
        data=result,
        message=f"Imported {result.successful_count} of {result.total_rows} leads.",
    )


# ─── CSV export ─────────────────────────────────────────────────────────────────


@router.get("/export")
async def export_leads(
    lead_ids: list[uuid.UUID] | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    status_filter: list[str] | None = Query(default=None, alias="status"),
    source: list[str] | None = Query(default=None),
    owner_id: list[uuid.UUID] | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    archived: bool | None = Query(default=None),
    user: User = Depends(require_permission("leads", "export")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    repo = LeadRepository(db)
    if lead_ids:
        leads = await repo.get_many_by_ids(lead_ids, user.organization_id)
    else:
        leads, _total = await repo.list_for_organization(
            user.organization_id,
            search=search,
            status=status_filter,
            source=source,
            owner_ids=owner_id,
            tag_names=tag,
            is_favorite=favorite,
            is_archived=archived,
            page=1,
            page_size=10_000,
        )
    csv_text = await LeadImportExportService(db).export_csv(
        organization_id=user.organization_id, leads=leads
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


# ─── Bulk actions ───────────────────────────────────────────────────────────────


@router.post("/bulk", response_model=ApiResponse[BulkActionResponse])
async def bulk_leads(
    payload: BulkLeadActionRequest,
    user: User = Depends(require_permission("leads", "bulk")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkActionResponse]:
    requested, success, errors = await LeadService(db).bulk_action(
        organization_id=user.organization_id, payload=payload, actor=user
    )
    return ApiResponse(
        data=BulkActionResponse(
            action=payload.action,
            requested_count=requested,
            success_count=success,
            failed_count=len(errors),
            errors=[
                BulkActionError(lead_id=str(lid), message=msg) for lid, msg in errors
            ],
        ),
        message=f"{success} of {requested} leads updated.",
    )


@router.post("/bulk/research", response_model=ApiResponse[BulkResearchResponse])
async def bulk_trigger_lead_research(
    payload: BulkLeadResearchRequest,
    user: User = Depends(require_permission("leads", "bulk")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkResearchResponse]:
    queued, errors = await ProspectAnalysisService(db).bulk_trigger_research(
        user.organization_id, payload.lead_ids, actor=user
    )
    return ApiResponse(
        data=BulkResearchResponse(
            requested_count=len(payload.lead_ids), queued_count=queued, errors=errors
        ),
        message=f"Research queued for {queued} of {len(payload.lead_ids)} leads.",
    )


@router.post("/bulk/generate-emails", response_model=ApiResponse[BulkEmailGenerationResponse])
async def bulk_generate_emails(
    payload: BulkLeadEmailGenerationRequest,
    user: User = Depends(require_permission("leads", "bulk")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkEmailGenerationResponse]:
    queued, errors = await EmailGenerationService(db).bulk_generate(
        user.organization_id, payload.lead_ids, actor=user,
        template_type=payload.template_type, tone=payload.tone, variant_count=payload.variant_count,
    )
    return ApiResponse(
        data=BulkEmailGenerationResponse(
            requested_count=len(payload.lead_ids), queued_count=queued, errors=errors
        ),
        message=f"Email generation queued for {queued} of {len(payload.lead_ids)} leads.",
    )


# ─── Lead CRUD by id ────────────────────────────────────────────────────────────


@router.get("/{lead_id}", response_model=ApiResponse[LeadResponse])
async def get_lead(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LeadResponse]:
    return ApiResponse(data=await _lead_response(lead_id, user.organization_id, db))


@router.patch("/{lead_id}", response_model=ApiResponse[LeadResponse])
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdateRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LeadResponse]:
    service = LeadService(db)
    lead = await service.require_lead(lead_id, user.organization_id)
    lead = await service.update(lead, payload=payload, actor=user)
    counts = (await LeadRepository(db).counts_for_leads([lead.id])).get(lead.id, {})
    return ApiResponse(
        data=serialize_lead(lead, counts=counts), message="Lead updated."
    )


@router.delete("/{lead_id}", response_model=ApiResponse[None])
async def delete_lead(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    service = LeadService(db)
    lead = await service.require_lead(lead_id, user.organization_id)
    await service.delete(lead, actor=user)
    return ApiResponse(message="Lead deleted.")


# ─── Research (AI -> Prospect Analysis, combined "Research this Lead") ──────────


async def _lead_research_status_response(
    lead_id: uuid.UUID, organization_id: uuid.UUID, db: AsyncSession
) -> LeadResearchStatusResponse:
    service = ProspectAnalysisService(db)
    lead = await service.require_lead(lead_id, organization_id)
    company_job, prospect_job = await service.get_lead_research_status(organization_id, lead)
    return LeadResearchStatusResponse(
        lead_id=str(lead.id),
        lead_status=lead.status,
        company_job=serialize_job(company_job) if company_job else None,
        prospect_job=serialize_job(prospect_job) if prospect_job else None,
    )


@router.post("/{lead_id}/research", response_model=ApiResponse[LeadResearchStatusResponse])
async def trigger_lead_research(
    lead_id: uuid.UUID,
    force: bool = Query(default=False),
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LeadResearchStatusResponse]:
    service = ProspectAnalysisService(db)
    await service.trigger_lead_research(user.organization_id, lead_id, actor=user, force=force)
    return ApiResponse(
        data=await _lead_research_status_response(lead_id, user.organization_id, db),
        message="Lead research started.",
    )


@router.get("/{lead_id}/research", response_model=ApiResponse[LeadResearchStatusResponse])
async def get_lead_research(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LeadResearchStatusResponse]:
    return ApiResponse(data=await _lead_research_status_response(lead_id, user.organization_id, db))


@router.get(
    "/{lead_id}/prospect-analysis", response_model=ApiResponse[ProspectAnalysisResponse | None]
)
async def get_prospect_analysis(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProspectAnalysisResponse | None]:
    service = ProspectAnalysisService(db)
    await service.require_lead(lead_id, user.organization_id)
    analysis = await service.analyses.get_by_lead(lead_id, user.organization_id)
    return ApiResponse(data=serialize_prospect_analysis(analysis) if analysis else None)


# ─── Email Generation (AI -> Personalized Email + Human Review) ─────────────────


@router.post("/{lead_id}/emails/generate", response_model=ApiResponse[AIJobResponse])
async def generate_lead_email(
    lead_id: uuid.UUID,
    payload: GenerateEmailRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIJobResponse]:
    job = await EmailGenerationService(db).generate_email(
        user.organization_id, lead_id, actor=user,
        template_type=payload.template_type, tone=payload.tone,
        variant_count=payload.variant_count, custom_instruction=payload.custom_instruction,
    )
    return ApiResponse(data=serialize_job(job), message="Email generation started.")


@router.get("/{lead_id}/emails/drafts", response_model=ApiResponse[list[EmailResponse]])
async def list_lead_email_drafts(
    lead_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[EmailResponse]]:
    """Despite the URL (kept for the Email Generation module's contract),
    this returns every Email for the lead by default, not just DRAFT-status
    ones — the Outreach tab needs a scheduled/sent email to stay visible
    after Send, not disappear the moment it leaves DRAFT. Pass `?status=draft`
    to filter, same as before."""
    service = EmailGenerationService(db)
    await service.require_lead(lead_id, user.organization_id)
    emails = await service.emails.list_for_lead(lead_id, user.organization_id, status=status_filter)
    return ApiResponse(data=[serialize_email(e) for e in emails])


@router.post("/{lead_id}/emails/regenerate", response_model=ApiResponse[AIJobResponse])
async def regenerate_lead_email(
    lead_id: uuid.UUID,
    payload: RegenerateEmailRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AIJobResponse]:
    service = EmailGenerationService(db)
    lead = await service.require_lead(lead_id, user.organization_id)
    source_output = await service.ai_outputs.get_by_id(payload.source_output_id, user.organization_id)
    if source_output is None:
        raise NotFoundError("Prior email variant not found.")
    source_job = await service.ai_jobs.get_by_id(source_output.job_id, user.organization_id)
    source_variables = (source_job.input_data or {}).get("variables", {}) if source_job else {}
    template_type = payload.template_type or EmailTemplateTypeEnum(
        source_variables.get("template_type", EmailTemplateTypeEnum.COLD_OUTREACH.value)
    )
    tone = payload.tone or EmailToneEnum(source_variables.get("tone", EmailToneEnum.PROFESSIONAL.value))
    job = await service.generate_email(
        user.organization_id, lead.id, actor=user, template_type=template_type, tone=tone,
        variant_count=payload.variant_count, custom_instruction=payload.custom_instruction,
        regenerate_from_output_id=payload.source_output_id,
    )
    return ApiResponse(data=serialize_job(job), message="Regeneration started.")


# ─── Email Sending (Communication -> Send Draft Email) ───────────────────────────


@router.post("/{lead_id}/emails/{email_id}/send", response_model=ApiResponse[EmailResponse])
async def send_lead_email(
    lead_id: uuid.UUID,
    email_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailResponse]:
    service = EmailSendingService(db)
    email = await service.require_email(email_id, user.organization_id)
    if email.lead_id != lead_id:
        raise NotFoundError("Email not found.")
    email = await service.send_now(user.organization_id, email_id, actor=user)
    return ApiResponse(data=serialize_email(email), message="Email sent.")


@router.post("/{lead_id}/emails/{email_id}/schedule", response_model=ApiResponse[EmailResponse])
async def schedule_lead_email(
    lead_id: uuid.UUID,
    email_id: uuid.UUID,
    payload: ScheduleEmailRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailResponse]:
    service = EmailSendingService(db)
    email = await service.require_email(email_id, user.organization_id)
    if email.lead_id != lead_id:
        raise NotFoundError("Email not found.")
    email = await service.schedule_send(
        user.organization_id, email_id, scheduled_at=payload.scheduled_at, actor=user
    )
    return ApiResponse(data=serialize_email(email), message="Email scheduled.")


@router.post("/{lead_id}/emails/{email_id}/cancel", response_model=ApiResponse[EmailResponse])
async def cancel_lead_email(
    lead_id: uuid.UUID,
    email_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailResponse]:
    service = EmailSendingService(db)
    email = await service.require_email(email_id, user.organization_id)
    if email.lead_id != lead_id:
        raise NotFoundError("Email not found.")
    email = await service.cancel_scheduled(user.organization_id, email_id, actor=user)
    return ApiResponse(data=serialize_email(email), message="Scheduled send cancelled.")


# ─── Notes ──────────────────────────────────────────────────────────────────────


@router.get("/{lead_id}/notes", response_model=ApiResponse[list[NoteResponse]])
async def list_notes(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NoteResponse]]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    notes = await NoteService(db).list_for_lead(lead_id)
    return ApiResponse(data=[serialize_note(n) for n in notes])


@router.post(
    "/{lead_id}/notes",
    response_model=ApiResponse[NoteResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    lead_id: uuid.UUID,
    payload: NoteCreateRequest,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NoteResponse]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    note = await NoteService(db).create(
        organization_id=user.organization_id,
        lead_id=lead_id,
        content=payload.content,
        is_pinned=payload.is_pinned,
        actor=user,
    )
    return ApiResponse(data=serialize_note(note), message="Note added.")


@router.patch("/{lead_id}/notes/{note_id}", response_model=ApiResponse[NoteResponse])
async def update_note(
    lead_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdateRequest,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NoteResponse]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    note = await NoteService(db).update(
        note_id=note_id,
        lead_id=lead_id,
        content=payload.content,
        is_pinned=payload.is_pinned,
        actor=user,
    )
    return ApiResponse(data=serialize_note(note), message="Note updated.")


@router.delete("/{lead_id}/notes/{note_id}", response_model=ApiResponse[None])
async def delete_note(
    lead_id: uuid.UUID,
    note_id: uuid.UUID,
    user: User = Depends(require_permission("notes", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    await NoteService(db).delete(note_id=note_id, lead_id=lead_id, actor=user)
    return ApiResponse(message="Note deleted.")


# ─── Activities ─────────────────────────────────────────────────────────────────


@router.get("/{lead_id}/activities", response_model=ApiResponse[list[ActivityResponse]])
async def list_activities(
    lead_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ActivityResponse]]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    activities, total = await ActivityRepository(db).list_for_lead(
        lead_id, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_activity(a) for a in activities],
        meta={"page": page, "page_size": page_size, "total": total},
    )


# ─── Attachments ────────────────────────────────────────────────────────────────


@router.post(
    "/{lead_id}/attachments",
    response_model=ApiResponse[AttachmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    lead_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("attachments", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AttachmentResponse]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    attachment = await AttachmentService(db).upload(
        organization_id=user.organization_id, lead_id=lead_id, file=file, actor=user
    )
    return ApiResponse(
        data=serialize_attachment(attachment), message="Attachment uploaded."
    )


@router.get(
    "/{lead_id}/attachments", response_model=ApiResponse[list[AttachmentResponse]]
)
async def list_attachments(
    lead_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AttachmentResponse]]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    attachments = await AttachmentService(db).list_for_lead(lead_id)
    return ApiResponse(data=[serialize_attachment(a) for a in attachments])


@router.delete(
    "/{lead_id}/attachments/{attachment_id}", response_model=ApiResponse[None]
)
async def delete_attachment(
    lead_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(require_permission("attachments", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await LeadService(db).require_lead(lead_id, user.organization_id)
    await AttachmentService(db).delete(attachment_id=attachment_id, lead_id=lead_id, actor=user)
    return ApiResponse(message="Attachment deleted.")
