"""ORM -> response-schema mapping for the Lead Management module."""

from app.models.crm.models import Activity, Attachment, Lead, Note, Tag
from app.schemas.leads import (
    ActivityResponse,
    AttachmentResponse,
    LeadAddress,
    LeadOwnerResponse,
    LeadResponse,
    NoteResponse,
    TagResponse,
)


def serialize_tag(tag: Tag) -> TagResponse:
    return TagResponse(id=str(tag.id), name=tag.name, color=tag.color)


def serialize_lead(lead: Lead, *, counts: dict[str, int] | None = None) -> LeadResponse:
    counts = counts or {"notes": 0, "attachments": 0, "activities": 0}
    return LeadResponse(
        id=str(lead.id),
        organization_id=str(lead.organization_id),
        first_name=lead.first_name,
        last_name=lead.last_name,
        full_name=lead.full_name,
        email=lead.email,
        phone=lead.phone,
        job_title=lead.job_title,
        company_name=lead.company_name,
        website=lead.website,
        industry=lead.industry,
        source=lead.source,
        status=lead.status,
        priority=lead.priority,
        country=lead.country,
        state=lead.state,
        city=lead.city,
        address=LeadAddress(**lead.address) if lead.address else None,
        linkedin_url=lead.linkedin_url,
        twitter_url=lead.twitter_url,
        company_size=lead.company_size,
        revenue=lead.revenue,
        employee_count=lead.employee_count,
        owner=(
            LeadOwnerResponse(
                id=str(lead.owner.id),
                full_name=lead.owner.full_name,
                email=lead.owner.email,
                avatar_url=lead.owner.avatar_url,
            )
            if lead.owner
            else None
        ),
        tags=[serialize_tag(tag) for tag in lead.tags],
        description=lead.description,
        lead_score=lead.lead_score,
        notes_count=counts.get("notes", 0),
        attachments_count=counts.get("attachments", 0),
        activities_count=counts.get("activities", 0),
        is_favorite=lead.is_favorite,
        is_archived=lead.is_archived,
        created_by=str(lead.created_by) if lead.created_by else None,
        updated_by=str(lead.updated_by) if lead.updated_by else None,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def serialize_note(note: Note) -> NoteResponse:
    return NoteResponse(
        id=str(note.id),
        lead_id=str(note.lead_id),
        author_id=str(note.author_id) if note.author_id else None,
        author_name=note.author.full_name if note.author else None,
        content=note.content,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def serialize_attachment(attachment: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=str(attachment.id),
        lead_id=str(attachment.lead_id),
        filename=attachment.filename,
        file_url=f"/media/{attachment.file_key}",
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        uploaded_by=str(attachment.uploaded_by) if attachment.uploaded_by else None,
        uploaded_by_name=attachment.uploader.full_name if attachment.uploader else None,
        created_at=attachment.created_at,
    )


def serialize_activity(activity: Activity) -> ActivityResponse:
    return ActivityResponse(
        id=str(activity.id),
        lead_id=str(activity.lead_id),
        actor_id=str(activity.actor_id) if activity.actor_id else None,
        actor_name=activity.actor.full_name if activity.actor else None,
        activity_type=activity.activity_type,
        summary=activity.summary,
        metadata=activity.metadata_,
        occurred_at=activity.occurred_at,
    )
