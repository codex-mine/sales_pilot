"""
Communication -> Email Sending Infrastructure.

Takes an approved DRAFT `Email` row (produced by the Email Generation
module) from DRAFT/SCHEDULED to SENT, or to FAILED with a captured reason.
Every dispatch path funnels through `_attempt_send`, which is the single
place suppression is checked, the daily limit is enforced, and the
compliance footer is injected — "do not treat this as just call an SMTP
API" per the module's own compliance mandate.

Retry model: rather than a separate Celery-native retry decorator, a
transient failure (outside a synchronous "Send Now" click) reschedules the
row a short backoff later (`current_status="scheduled"`, `scheduled_at`
bumped) — the periodic due-scheduled dispatcher (`app/workers/
email_sending_tasks.py`) naturally retries it on its next pass. This reuses
the scheduling mechanism as the retry mechanism instead of building a
second one, while `send_retry_count`/`send_error` on the Email row still
give the outbox UI the same visibility AIJob's retry_count/error_message do.
"""

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import EmailSendError, NotFoundError, RecipientSuppressedError, ValidationError
from app.models.campaigns.models import Campaign, CampaignLead
from app.models.communication.models import Conversation, Email
from app.models.crm.models import Lead
from app.models.enums import ActivityTypeEnum, AuditActionEnum, LeadStatusEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.email_template_repository import EmailTemplateRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.leads import LeadUpdateRequest
from app.security.tokens import create_unsubscribe_token
from app.services.email.email_sender_settings_service import EmailSenderSettingsService
from app.services.email.email_tracking_service import EmailTrackingService
from app.services.email.sender_client import get_sender_client
from app.services.lead_service import LeadService
from app.services.system_actor import resolve_org_owner

_UNSENDABLE_STATUSES = {"sent", "delivered", "opened", "clicked", "bounced", "spam"}
_DEFAULT_SEND_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


class EmailSendingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.emails = EmailRepository(db)
        self.leads = LeadRepository(db)
        self.organizations = OrganizationRepository(db)
        self.sender_settings = EmailSenderSettingsService(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.lead_service = LeadService(db)
        self.templates = EmailTemplateRepository(db)

    async def require_email(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> Email:
        email = await self.emails.get_by_id(email_id, organization_id)
        if email is None:
            raise NotFoundError("Email not found.")
        return email

    # ─── Public actions ─────────────────────────────────────────────────────────

    async def send_now(self, organization_id: uuid.UUID, email_id: uuid.UUID, *, actor: User) -> Email:
        email = await self._require_locked(email_id, organization_id)
        return await self._attempt_send(email, actor=actor, mark_failed_immediately=True)

    async def schedule_send(
        self, organization_id: uuid.UUID, email_id: uuid.UUID, *, scheduled_at: datetime, actor: User
    ) -> Email:
        email = await self._require_locked(email_id, organization_id)
        if email.current_status not in ("draft", "failed"):
            raise ValidationError("Only draft or failed emails can be scheduled.")
        if scheduled_at <= datetime.now(timezone.utc):
            raise ValidationError(
                "Scheduled time must be in the future.", errors={"scheduled_at": ["Must be in the future."]}
            )
        email = await self.emails.update(
            email,
            {"current_status": "scheduled", "scheduled_at": scheduled_at, "send_error": None, "sent_by": actor.id},
            updated_by=actor.id,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": "email_scheduled", "scheduled_at": scheduled_at.isoformat()},
        )
        await self.db.commit()
        return await self.require_email(email.id, organization_id)

    async def cancel_scheduled(self, organization_id: uuid.UUID, email_id: uuid.UUID, *, actor: User) -> Email:
        email = await self._require_locked(email_id, organization_id)
        if email.current_status != "scheduled":
            raise ValidationError("Only a scheduled email can be cancelled.")
        email = await self.emails.update(
            email,
            {"current_status": "draft", "scheduled_at": None, "send_error": None, "send_retry_count": 0},
            updated_by=actor.id,
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": "email_send_cancelled"},
        )
        await self.db.commit()
        return await self.require_email(email.id, organization_id)

    async def bulk_send(
        self, organization_id: uuid.UUID, lead_ids: list[str], *, actor: User
    ) -> tuple[int, int, list[str]]:
        errors: list[str] = []
        parsed_ids: list[uuid.UUID] = []
        for raw_id in lead_ids:
            try:
                parsed_ids.append(uuid.UUID(raw_id))
            except ValueError:
                errors.append(f"{raw_id}: not a valid lead id.")

        success = 0
        for lead_id in parsed_ids:
            drafts = await self.emails.list_for_lead(lead_id, organization_id, status="draft")
            if not drafts:
                errors.append(f"{lead_id}: no draft email to send.")
                continue
            try:
                email = await self._require_locked(drafts[0].id, organization_id)
                await self._attempt_send(email, actor=actor, mark_failed_immediately=True)
                success += 1
            except (RecipientSuppressedError, EmailSendError, ValidationError, NotFoundError) as exc:
                errors.append(f"{lead_id}: {exc}")

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=None,
            changes={"event": "bulk_send_triggered", "requested": len(lead_ids), "success": success, "failed": len(errors)},
        )
        await self.db.commit()
        return len(lead_ids), success, errors

    async def process_scheduled(self, email_id: uuid.UUID, organization_id: uuid.UUID, actor: User) -> Email:
        """The scheduler's per-row entry point (`app/workers/
        email_sending_tasks.py`). Re-locks and re-checks status itself, so a
        redelivered/duplicate Celery task for the same row is a safe no-op."""
        email = await self._require_locked(email_id, organization_id)
        if email.current_status != "scheduled":
            return email
        return await self._attempt_send(email, actor=actor, mark_failed_immediately=False)

    async def preview(self, organization_id: uuid.UUID, email_id: uuid.UUID) -> dict:
        email = await self.require_email(email_id, organization_id)
        lead = await self.leads.get_by_id(email.lead_id, organization_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        organization = await self.organizations.get_by_id(organization_id)
        body_html, body_text, unsubscribe_url = self._inject_compliance_footer(email, lead, organization)
        body_html, body_text = await EmailTrackingService(self.db).instrument_content(
            email, body_html, body_text, unsubscribe_url
        )
        await self.db.commit()  # persists tracking_pixel_id if this is the first time it was generated
        return {
            "subject": email.subject, "body_html": body_html, "body_text": body_text,
            "to_email": email.to_email, "to_name": email.to_name,
            "from_email": email.from_email, "from_name": email.from_name,
        }

    # ─── Guarded send attempt (shared by send_now / bulk_send / scheduler) ──────

    async def _require_locked(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> Email:
        email = await self.emails.get_for_update(email_id, organization_id)
        if email is None:
            raise NotFoundError("Email not found.")
        return email

    async def _attempt_send(self, email: Email, *, actor: User, mark_failed_immediately: bool) -> Email:
        if email.current_status in _UNSENDABLE_STATUSES:
            return email  # idempotency guard — never re-send an already-dispatched email

        lead = await self.leads.get_by_id(email.lead_id, email.organization_id)
        if lead is None:
            await self.emails.update(
                email, {"current_status": "failed", "send_error": "Lead not found."}, updated_by=actor.id
            )
            await self.db.commit()
            raise NotFoundError("Lead not found.")

        # Suppression — the LAST gate, immediately before dispatch. A lead
        # could have unsubscribed between draft-approval and send time.
        suppressed_reason = await self._suppression_reason(lead, email)
        if suppressed_reason:
            await self.emails.update(
                email, {"current_status": "failed", "send_error": suppressed_reason}, updated_by=actor.id
            )
            await self.audit_log.record(
                organization_id=email.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
                changes={"event": "email_send_failed", "reason": suppressed_reason},
            )
            await self.db.commit()
            raise RecipientSuppressedError(suppressed_reason)

        # Daily send limit — defer to the next window rather than fail outright.
        limit = await self.sender_settings.daily_send_limit(email.organization_id)
        sent_today = await self.emails.count_sent_today(email.organization_id)
        if sent_today >= limit:
            organization = await self.organizations.get_by_id(email.organization_id)
            next_slot = self._next_send_window_start(organization.timezone if organization else "UTC")
            await self.emails.update(
                email, {"current_status": "scheduled", "scheduled_at": next_slot}, updated_by=actor.id
            )
            await self.audit_log.record(
                organization_id=email.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email", resource_id=None,
                changes={"event": "daily_send_limit_reached", "limit": limit, "deferred_to": next_slot.isoformat()},
            )
            await self.db.commit()
            return email

        # Send-window: only enforced for automated dispatch, not an explicit
        # "Send Now" click — see module docstring's judgment call.
        if not mark_failed_immediately:
            organization = await self.organizations.get_by_id(email.organization_id)
            if not await self._within_send_window(email, organization):
                return email  # left as-is; the scheduler reconsiders it next tick

        credentials = await self.sender_settings.resolve_credentials(email.organization_id)
        if credentials is None:
            message = "No outreach sending mailbox is configured for this organization."
            await self.emails.update(email, {"current_status": "failed", "send_error": message}, updated_by=actor.id)
            await self.audit_log.record(
                organization_id=email.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
                changes={"event": "email_send_failed", "reason": message},
            )
            await self.db.commit()
            raise EmailSendError(message)
        host, port, username, password, use_tls = credentials

        organization = await self.organizations.get_by_id(email.organization_id)
        final_html, final_text, unsubscribe_url = self._inject_compliance_footer(email, lead, organization)
        final_html, final_text = await EmailTrackingService(self.db).instrument_content(
            email, final_html, final_text, unsubscribe_url
        )
        await self.emails.update(email, {"current_status": "sending"}, updated_by=actor.id)
        await self.db.commit()

        client = get_sender_client("smtp", host=host, port=port, username=username, password=password, use_tls=use_tls)
        try:
            result = await client.send(
                from_email=email.from_email, from_name=email.from_name,
                to_email=email.to_email, to_name=email.to_name, reply_to=email.reply_to,
                subject=email.subject, body_html=final_html, body_text=final_text,
            )
        except EmailSendError as exc:
            return await self._handle_send_failure(email, exc, actor=actor, mark_failed_immediately=mark_failed_immediately)

        await self.emails.update(
            email,
            {
                "current_status": "sent", "sent_at": datetime.now(timezone.utc),
                "external_message_id": result.external_message_id,
                "body_html": final_html, "body_text": final_text, "sent_by": actor.id,
            },
            updated_by=actor.id,
        )
        await self._attach_conversation(email, lead)
        await EmailTrackingService(self.db).record_sent(email)
        if email.email_template_id:
            template = await self.templates.get_by_id(email.email_template_id, email.organization_id)
            if template is not None:
                template.total_sent += 1
                await self.db.flush()
        await self.activities.record(
            organization_id=email.organization_id, lead_id=lead.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.EMAIL_SENT,
            summary=f"Email sent to {lead.full_name} by {actor.full_name}",
        )
        fresh_lead = await self.leads.get_by_id(lead.id, lead.organization_id)
        if fresh_lead is not None and fresh_lead.status in (
            LeadStatusEnum.NEW.value, LeadStatusEnum.RESEARCHING.value,
            LeadStatusEnum.RESEARCH_DONE.value, LeadStatusEnum.EMAIL_GENERATED.value,
        ):
            await self.lead_service.update(
                fresh_lead, payload=LeadUpdateRequest(status=LeadStatusEnum.CONTACTED.value), actor=actor
            )
        await self.audit_log.record(
            organization_id=email.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": "email_sent", "external_message_id": result.external_message_id},
        )
        await self.db.commit()
        return await self.require_email(email.id, email.organization_id)

    async def _handle_send_failure(
        self, email: Email, exc: EmailSendError, *, actor: User, mark_failed_immediately: bool
    ) -> Email:
        new_retry_count = email.send_retry_count + 1
        max_retries = get_settings().outreach_send_max_retries
        if not mark_failed_immediately and new_retry_count <= max_retries:
            backoff_seconds = 60 * (2 ** (new_retry_count - 1))
            email = await self.emails.update(
                email,
                {
                    "current_status": "scheduled",
                    "scheduled_at": datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds),
                    "send_error": str(exc), "send_retry_count": new_retry_count,
                },
                updated_by=actor.id,
            )
            await self.db.commit()
            return email
        email = await self.emails.update(
            email, {"current_status": "failed", "send_error": str(exc), "send_retry_count": new_retry_count},
            updated_by=actor.id,
        )
        await self.audit_log.record(
            organization_id=email.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": "email_send_failed", "error": str(exc), "retry_count": new_retry_count},
        )
        await self.db.commit()
        raise exc

    # ─── Suppression / limits / window helpers ───────────────────────────────────

    async def _suppression_reason(self, lead: Lead, email: Email) -> str | None:
        if lead.status in (LeadStatusEnum.UNSUBSCRIBED.value, LeadStatusEnum.BOUNCED.value):
            return f"Recipient has status '{lead.status}'."
        prior_bounce = await self.emails.get_prior_hard_bounce(email.organization_id, email.to_email)
        if prior_bounce is not None:
            return "This address has a prior hard bounce on file."
        return None

    def _next_send_window_start(self, org_timezone: str) -> datetime:
        settings = get_settings()
        try:
            tz = ZoneInfo(org_timezone or "UTC")
        except Exception:  # noqa: BLE001 — bad/unknown tz string, fall back safely
            tz = ZoneInfo("UTC")
        local_now = datetime.now(tz)
        next_day = (local_now + timedelta(days=1)).replace(
            hour=settings.outreach_default_send_start_hour, minute=0, second=0, microsecond=0
        )
        return next_day.astimezone(timezone.utc)

    async def _resolve_send_window(
        self, email: Email
    ) -> tuple[list[str], int, int, str]:
        if email.campaign_lead_id:
            campaign = await self.db.scalar(
                select(Campaign)
                .join(CampaignLead, CampaignLead.campaign_id == Campaign.id)
                .where(CampaignLead.id == email.campaign_lead_id)
            )
            if campaign is not None:
                return (campaign.send_days or _DEFAULT_SEND_DAYS, campaign.send_start_hour, campaign.send_end_hour, campaign.timezone)
        settings = get_settings()
        organization = await self.organizations.get_by_id(email.organization_id)
        return (
            _DEFAULT_SEND_DAYS, settings.outreach_default_send_start_hour,
            settings.outreach_default_send_end_hour, (organization.timezone if organization else "UTC"),
        )

    async def _within_send_window(self, email: Email, organization) -> bool:
        send_days, start_hour, end_hour, tz_name = await self._resolve_send_window(email)
        try:
            tz = ZoneInfo(tz_name or "UTC")
        except Exception:  # noqa: BLE001
            tz = ZoneInfo("UTC")
        local_now = datetime.now(tz)
        day_name = local_now.strftime("%A").lower()
        return day_name in send_days and start_hour <= local_now.hour < end_hour

    # ─── Compliance footer (CAN-SPAM: unsubscribe link + org identity) ──────────

    def _inject_compliance_footer(self, email: Email, lead: Lead, organization) -> tuple[str, str, str]:
        """Injected server-side at send time — never trusted from the
        AI-generated or user-edited body, so it can't be accidentally
        stripped or edited out. The stored Draft/AIOutput content stays pure;
        only the actually-dispatched (and then-persisted) body carries it."""
        settings = get_settings()
        token = create_unsubscribe_token(str(lead.id), str(email.organization_id))
        unsubscribe_url = f"{settings.frontend_url}/unsubscribe/{token}"
        org_name = organization.name if organization else "SalesPilot"
        address_parts = []
        if organization and organization.address:
            address_parts = [v for v in organization.address.values() if v]
        org_address = ", ".join(str(p) for p in address_parts) if address_parts else None

        html_footer = (
            '<hr style="margin-top:24px;border:none;border-top:1px solid #E5E7EB;" />'
            '<p style="margin-top:12px;font-size:12px;line-height:18px;color:#9CA3AF;">'
            f"{org_name}"
            + (f", {org_address}" if org_address else "")
            + f'<br />Don\'t want to hear from us? <a href="{unsubscribe_url}" style="color:#6B7280;">Unsubscribe</a>.'
            "</p>"
        )
        text_footer = (
            f"\n\n---\n{org_name}" + (f", {org_address}" if org_address else "")
            + f"\nUnsubscribe: {unsubscribe_url}"
        )
        return (email.body_html or "") + html_footer, (email.body_text or "") + text_footer, unsubscribe_url

    # ─── Conversation threading ─────────────────────────────────────────────────

    async def _attach_conversation(self, email: Email, lead: Lead) -> None:
        if email.conversation_id:
            return
        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.organization_id == email.organization_id,
                Conversation.lead_id == lead.id,
                Conversation.is_active.is_(True),
            )
        )
        now = datetime.now(timezone.utc)
        if conversation is None:
            conversation = Conversation(
                organization_id=email.organization_id, lead_id=lead.id, subject=email.subject,
                is_active=True, last_message_at=now, message_count=1,
            )
            self.db.add(conversation)
            await self.db.flush()
        else:
            conversation.last_message_at = now
            conversation.message_count += 1
        email.conversation_id = conversation.id
        await self.db.flush()

    # ─── Unsubscribe ────────────────────────────────────────────────────────────

    async def get_unsubscribe_info(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> dict:
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("This link is invalid or has expired.")
        organization = await self.organizations.get_by_id(organization_id)
        return {
            "lead_first_name": lead.first_name,
            "organization_name": organization.name if organization else "SalesPilot",
            "already_unsubscribed": lead.status == LeadStatusEnum.UNSUBSCRIBED.value,
        }

    async def process_unsubscribe(self, lead_id: uuid.UUID, organization_id: uuid.UUID) -> dict:
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("This link is invalid or has expired.")
        if lead.status != LeadStatusEnum.UNSUBSCRIBED.value:
            try:
                system_user = await resolve_org_owner(self.db, organization_id)
            except NotFoundError as exc:
                raise NotFoundError("This link is invalid or has expired.") from exc
            await self.lead_service.update(
                lead, payload=LeadUpdateRequest(status=LeadStatusEnum.UNSUBSCRIBED.value), actor=system_user
            )
            await self.audit_log.record(
                organization_id=organization_id, actor_id=None, actor_email=None,
                action=AuditActionEnum.UPDATE, resource_type="lead", resource_id=lead.id,
                changes={"event": "unsubscribe_processed"},
            )
            await self.db.commit()
        organization = await self.organizations.get_by_id(organization_id)
        return {"lead_first_name": lead.first_name, "organization_name": organization.name if organization else "SalesPilot"}
