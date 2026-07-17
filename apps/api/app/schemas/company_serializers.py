"""ORM -> response-schema mapping for the Company module."""

from app.models.crm.models import Activity, Attachment, Company, Contact, Note, Tag
from app.schemas.companies import (
    CompanyActivityResponse,
    CompanyAddress,
    CompanyAttachmentResponse,
    CompanyEmployeeResponse,
    CompanyNoteResponse,
    CompanyOwnerResponse,
    CompanyResponse,
    CompanyTagResponse,
)


def serialize_company_tag(tag: Tag) -> CompanyTagResponse:
    return CompanyTagResponse(id=str(tag.id), name=tag.name, color=tag.color)


def serialize_company(company: Company, *, counts: dict[str, int] | None = None) -> CompanyResponse:
    counts = counts or {"notes": 0, "attachments": 0, "contacts": 0, "leads": 0}
    return CompanyResponse(
        id=str(company.id),
        organization_id=str(company.organization_id),
        name=company.name,
        legal_name=company.legal_name,
        logo_url=company.logo_url,
        website=company.website,
        domain=company.domain,
        industry=company.industry,
        description=company.description,
        phone=company.phone,
        email=company.email,
        founded_year=company.founded_year,
        size_range=company.size_range,
        employee_count=company.employee_count,
        annual_revenue=company.annual_revenue,
        currency=company.currency,
        country=company.country,
        state=company.state,
        city=company.city,
        postal_code=company.postal_code,
        address=CompanyAddress(**company.address) if company.address else None,
        linkedin_url=company.linkedin_url,
        twitter_url=company.twitter_url,
        facebook_url=company.facebook_url,
        instagram_url=company.instagram_url,
        status=company.status,
        owner=(
            CompanyOwnerResponse(
                id=str(company.owner.id),
                full_name=company.owner.full_name,
                email=company.owner.email,
                avatar_url=company.owner.avatar_url,
            )
            if company.owner
            else None
        ),
        tags=[serialize_company_tag(tag) for tag in company.tags],
        contact_count=counts.get("contacts", 0),
        lead_count=counts.get("leads", 0),
        notes_count=counts.get("notes", 0),
        attachments_count=counts.get("attachments", 0),
        is_archived=company.is_archived,
        created_by=str(company.created_by) if company.created_by else None,
        updated_by=str(company.updated_by) if company.updated_by else None,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def serialize_company_note(note: Note) -> CompanyNoteResponse:
    return CompanyNoteResponse(
        id=str(note.id),
        company_id=str(note.company_id),
        author_id=str(note.author_id) if note.author_id else None,
        author_name=note.author.full_name if note.author else None,
        content=note.content,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def serialize_company_attachment(attachment: Attachment) -> CompanyAttachmentResponse:
    return CompanyAttachmentResponse(
        id=str(attachment.id),
        company_id=str(attachment.company_id),
        filename=attachment.filename,
        file_url=f"/media/{attachment.file_key}",
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        uploaded_by=str(attachment.uploaded_by) if attachment.uploaded_by else None,
        uploaded_by_name=attachment.uploader.full_name if attachment.uploader else None,
        created_at=attachment.created_at,
    )


def serialize_company_activity(activity: Activity) -> CompanyActivityResponse:
    return CompanyActivityResponse(
        id=str(activity.id),
        company_id=str(activity.company_id),
        actor_id=str(activity.actor_id) if activity.actor_id else None,
        actor_name=activity.actor.full_name if activity.actor else None,
        activity_type=activity.activity_type,
        summary=activity.summary,
        metadata=activity.metadata_,
        occurred_at=activity.occurred_at,
    )


def serialize_employee(contact: Contact) -> CompanyEmployeeResponse:
    return CompanyEmployeeResponse(
        id=str(contact.id),
        full_name=contact.full_name,
        job_title=contact.job_title,
        department=contact.department,
        email=contact.email,
        phone=contact.phone,
        status=contact.status,
        is_decision_maker=contact.is_decision_maker,
        has_linked_lead=len(contact.leads) > 0,
        last_activity_at=contact.updated_at,
        created_at=contact.created_at,
    )
