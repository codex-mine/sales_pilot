"""ORM -> response-schema mapping for the Email Generation and Email Sending
modules."""

import enum

from app.models.campaigns.models import EmailTemplate
from app.models.communication.models import Email
from app.models.remaining_domains import Integration
from app.schemas.email_generation import EmailResponse, EmailTemplateResponse
from app.schemas.email_sending import OutboxEmailResponse, SenderMailboxResponse


def _ev(value):
    """Enum-safe string — see app.schemas.ai_serializers._ev for why this is
    needed (freshly-created rows hold the enum instance, DB-loaded rows hold
    the plain string)."""
    if value is None:
        return None
    return value.value if isinstance(value, enum.Enum) else str(value)


def serialize_email(email: Email) -> EmailResponse:
    return EmailResponse(
        id=str(email.id),
        lead_id=str(email.lead_id),
        from_email=email.from_email,
        from_name=email.from_name,
        to_email=email.to_email,
        to_name=email.to_name,
        subject=email.subject,
        body_html=email.body_html,
        body_text=email.body_text,
        current_status=_ev(email.current_status),
        ai_generated=email.ai_generated,
        personalization_data=email.personalization_data,
        scheduled_at=email.scheduled_at,
        sent_at=email.sent_at,
        created_at=email.created_at,
    )


def serialize_outbox_email(email: Email, *, bounce_reason: str | None = None) -> OutboxEmailResponse:
    lead = email.lead
    return OutboxEmailResponse(
        id=str(email.id),
        lead_id=str(email.lead_id),
        lead_full_name=lead.full_name if lead else None,
        lead_company_name=lead.company_name if lead else None,
        from_email=email.from_email,
        from_name=email.from_name,
        to_email=email.to_email,
        to_name=email.to_name,
        subject=email.subject,
        current_status=_ev(email.current_status),
        ai_generated=email.ai_generated,
        send_error=email.send_error,
        send_retry_count=email.send_retry_count,
        bounce_reason=bounce_reason,
        scheduled_at=email.scheduled_at,
        sent_at=email.sent_at,
        created_at=email.created_at,
    )


def serialize_email_template(template: EmailTemplate) -> EmailTemplateResponse:
    return EmailTemplateResponse(
        id=str(template.id),
        organization_id=str(template.organization_id),
        ai_job_id=str(template.ai_job_id) if template.ai_job_id else None,
        name=template.name,
        template_type=_ev(template.template_type),
        tone=_ev(template.tone),
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        ai_reasoning=template.ai_reasoning,
        variables_used=template.variables_used,
        is_active=template.is_active,
        is_ai_generated=template.is_ai_generated,
        version=template.version,
        total_sent=template.total_sent,
        total_opened=template.total_opened,
        total_replied=template.total_replied,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def serialize_sender_mailbox(mailbox: Integration) -> SenderMailboxResponse:
    config = mailbox.config or {}
    use_tls = bool(config.get("use_tls", True))
    return SenderMailboxResponse(
        id=str(mailbox.id),
        name=mailbox.name,
        email_address=mailbox.external_account_email,
        host=config.get("host", ""),
        port=int(config.get("port", 587)),
        username=config.get("username"),
        encryption_type=config.get("encryption_type") or ("starttls" if use_tls else "none"),
        from_name=config.get("from_name"),
        reply_to=config.get("reply_to"),
        is_default=bool(config.get("is_default", False)),
        is_active=mailbox.is_active,
        daily_send_limit=config.get("daily_send_limit"),
        created_at=mailbox.created_at,
        updated_at=mailbox.updated_at,
    )
