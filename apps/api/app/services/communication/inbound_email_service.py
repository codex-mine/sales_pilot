"""
Communication -> Inbox & AI Reply Classification.

`ingest_reply` is the single entry point for a prospect's reply landing in
the system, whichever provider's webhook delivered it. Classification never
calls an LLM SDK directly — it goes through `AIJobService.run_job(...)`
exactly like every other AI-touching module built on the AI Foundation.

Tenant resolution for the (public, unauthenticated) inbound webhook never
trusts caller-supplied data: the organization is resolved either from a
prior sent Email's to/from pairing (the common "reply in an existing
thread" case) or from `Organization.domain` — never from anything the
payload itself claims about which org it belongs to.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.ai.models import AIJob
from app.models.communication.models import Conversation, Message
from app.models.crm.models import Lead
from app.models.enums import (
    ActivityTypeEnum,
    AIAgentTypeEnum,
    AIJobStatusEnum,
    AuditActionEnum,
    LeadStatusEnum,
    NotificationTypeEnum,
    ReplyClassificationEnum,
)
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.leads import LeadCreateRequest, LeadUpdateRequest
from app.services.ai.ai_job_service import AIJobService
from app.services.communication.inbound_parser import ParsedInboundEmail, parse_inbound_payload
from app.services.lead_service import LeadService
from app.services.lead_status_resolver import next_lead_status
from app.services.lead_suppression import suppress_lead
from app.services.system_actor import resolve_org_owner

logger = structlog.get_logger(__name__)

_TERMINAL_JOB_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}
_REPLIED_ONLY_CLASSIFICATIONS = {
    ReplyClassificationEnum.NOT_INTERESTED, ReplyClassificationEnum.NEEDS_FOLLOW_UP,
    ReplyClassificationEnum.REFERRAL, ReplyClassificationEnum.OUT_OF_OFFICE,
    ReplyClassificationEnum.SPAM, ReplyClassificationEnum.UNKNOWN,
}


class InboundEmailService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.emails = EmailRepository(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.leads = LeadRepository(db)
        self.organizations = OrganizationRepository(db)
        self.notifications = NotificationRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.lead_service = LeadService(db)
        self.ai_job_service = AIJobService(db)

    # ─── Ingestion ──────────────────────────────────────────────────────────────

    async def ingest_reply(self, provider: str, payload: dict) -> Message | None:
        parsed = parse_inbound_payload(provider, payload)

        if parsed.external_message_id:
            existing = await self.messages.get_by_external_message_id(parsed.external_message_id)
            if existing is not None:
                return existing  # redelivered webhook — idempotent no-op

        resolution = await self._resolve_organization_and_lead(parsed)
        if resolution is None:
            logger.warning("inbound_reply_unresolvable_tenant", to_email=parsed.to_email)
            return None  # cannot attribute this to any tenant — nothing valid to store it under

        organization_id, lead, is_matched = resolution

        conversation = await self.conversations.get_open_for_lead(lead.id, organization_id)
        if conversation is None:
            conversation = await self.conversations.create(
                organization_id=organization_id, lead_id=lead.id, subject=parsed.subject, is_active=True,
            )

        in_reply_to_email_id = await self._resolve_in_reply_to(conversation, parsed)

        message = await self.messages.create(
            organization_id=organization_id, conversation_id=conversation.id, lead_id=lead.id,
            in_reply_to_email_id=in_reply_to_email_id,
            from_email=parsed.from_email, from_name=parsed.from_name, subject=parsed.subject,
            body_text=parsed.body_text, body_html=parsed.body_html,
            external_message_id=parsed.external_message_id,
            reply_classification=None if is_matched else ReplyClassificationEnum.UNKNOWN.value,
            ai_suggested_action=None if is_matched else "Unmatched sender — review and link to the correct lead.",
        )
        await self.conversations.touch(conversation)

        try:
            system_actor = await resolve_org_owner(self.db, organization_id)
        except NotFoundError:
            system_actor = None

        if is_matched and system_actor is not None:
            new_status = next_lead_status(lead.status, LeadStatusEnum.REPLIED)
            if new_status != lead.status:
                await self.lead_service.update(lead, payload=LeadUpdateRequest(status=new_status), actor=system_actor)

        await self.activities.record(
            organization_id=organization_id, lead_id=lead.id, actor_id=None,
            activity_type=ActivityTypeEnum.EMAIL_REPLIED,
            summary=f"Reply received from {lead.full_name}" if is_matched
            else f"Reply received from unmatched sender {parsed.from_email}",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.CREATE, resource_type="message", resource_id=message.id,
            changes={"event": "reply_ingested", "matched": is_matched},
        )
        await self._notify_owner(organization_id, lead, message)
        await self.db.commit()

        if is_matched:
            await self._trigger_classification(organization_id, lead, message)

        return message

    async def _resolve_organization_and_lead(self, parsed: ParsedInboundEmail) -> tuple[uuid.UUID, Lead, bool] | None:
        # Primary: the most recent Email we sent FROM the address this
        # reply arrived AT and TO the address this reply arrived FROM —
        # resolves both the organization and the lead in one step, exactly
        # how a real reply-in-thread works.
        matched_email = await self.emails.find_correspondence(parsed.from_email, parsed.to_email)
        if matched_email is not None:
            lead = await self.leads.get_by_id(matched_email.lead_id, matched_email.organization_id)
            if lead is not None:
                return matched_email.organization_id, lead, True

        # Fallback: resolve the organization by the recipient domain, then
        # look up the lead by sender email within that org.
        to_domain = parsed.to_email.rsplit("@", 1)[-1] if "@" in parsed.to_email else None
        if not to_domain:
            return None
        organization = await self.organizations.get_by_domain(to_domain)
        if organization is None:
            return None  # cannot attribute this to any tenant

        lead = await self.leads.get_by_email(organization.id, parsed.from_email)
        if lead is not None:
            return organization.id, lead, True

        # Organization resolved but no matching lead — auto-create a
        # minimal stub Lead so the reply isn't dropped (Message.lead_id is
        # NOT NULL, so there's nowhere else to attach it) and flag it via
        # UNKNOWN classification + a note, per the module's "still store the
        # message, don't drop data" requirement.
        try:
            system_actor = await resolve_org_owner(self.db, organization.id)
        except NotFoundError:
            return None
        stub_lead = await self.lead_service.create(
            organization_id=organization.id,
            payload=LeadCreateRequest(
                first_name=parsed.from_name, email=parsed.from_email, source="inbound_reply",
            ),
            actor=system_actor,
        )
        return organization.id, stub_lead, False

    async def _resolve_in_reply_to(self, conversation: Conversation, parsed: ParsedInboundEmail) -> uuid.UUID | None:
        if parsed.in_reply_to:
            matched = await self.emails.get_by_external_message_id(parsed.in_reply_to)
            if matched is not None and matched.conversation_id == conversation.id:
                return matched.id
        latest = await self.emails.get_latest_for_conversation(conversation.id)
        return latest.id if latest else None

    async def _notify_owner(self, organization_id: uuid.UUID, lead: Lead, message: Message) -> None:
        if not lead.owner_id:
            return
        await self.notifications.create(
            organization_id=organization_id, user_id=lead.owner_id,
            notification_type=NotificationTypeEnum.NEW_REPLY.value,
            title=f"New reply from {lead.full_name}",
            body=(message.body_text or "")[:280],
            entity_type="message", entity_id=message.id,
            action_url=f"/inbox?conversation={message.conversation_id}",
        )

    # ─── Classification (AI + manual) ────────────────────────────────────────────

    async def _trigger_classification(self, organization_id: uuid.UUID, lead: Lead, message: Message) -> AIJob:
        job = await self.ai_job_service.run_job(
            organization_id=organization_id, job_type="classify_reply", entity_type="message", entity_id=message.id,
            prompt_template_name="classify_reply",
            variables={
                "lead_first_name": lead.first_name or "",
                "original_subject": message.subject or "",
                "reply_body": message.body_text,
            },
            agent_type=AIAgentTypeEnum.REPLY_ANALYSIS, initiated_by=None, response_format="json",
        )
        if job.status in _TERMINAL_JOB_STATUSES:
            await self.finalize_classification(job, message.id, organization_id)
        else:
            from app.workers.inbox_tasks import finalize_reply_classification

            finalize_reply_classification.apply_async(
                args=[str(job.id), str(organization_id), str(message.id)], queue="inbox"
            )
        return job

    async def finalize_classification(self, job: AIJob, message_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        if job.status != AIJobStatusEnum.COMPLETED:
            return  # leave classification null — surfaces as "unclassified", never a silently wrong guess

        raw_output = job.outputs[-1] if job.outputs else None
        parsed = raw_output.content_json if raw_output else None
        if not isinstance(parsed, dict):
            return

        classification_raw = parsed.get("classification")
        try:
            classification = ReplyClassificationEnum(classification_raw)
        except ValueError:
            classification = ReplyClassificationEnum.UNKNOWN
            logger.warning("reply_classification_out_of_enum", value=classification_raw, message_id=str(message_id))

        confidence = parsed.get("confidence")
        suggested_action = parsed.get("suggested_action")

        message = await self.messages.get_by_id(message_id, organization_id)
        if message is None:
            return
        await self.messages.update(
            message,
            {
                "reply_classification": classification.value, "ai_suggested_action": suggested_action,
                "ai_confidence": confidence, "ai_classified_at": datetime.now(timezone.utc),
            },
        )

        lead = await self.leads.get_by_id(message.lead_id, organization_id)
        if lead is not None:
            try:
                actor = await resolve_org_owner(self.db, organization_id)
            except NotFoundError:
                actor = None
            if actor is not None:
                await self._apply_classification_side_effects(lead, classification, actor)

        await self.audit_log.record(
            organization_id=organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.UPDATE, resource_type="message", resource_id=message.id,
            changes={"event": "reply_classified_ai", "classification": classification.value, "confidence": confidence},
        )
        await self.db.commit()

    async def reclassify_message(
        self, organization_id: uuid.UUID, message_id: uuid.UUID, *, classification: ReplyClassificationEnum, actor: User
    ) -> Message:
        message = await self.messages.get_by_id(message_id, organization_id)
        if message is None:
            raise NotFoundError("Message not found.")
        previous = message.reply_classification
        await self.messages.update(message, {"reply_classification": classification.value})

        lead = await self.leads.get_by_id(message.lead_id, organization_id)
        if lead is not None:
            await self._apply_classification_side_effects(lead, classification, actor)

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="message", resource_id=message.id,
            changes={"event": "reply_reclassified_manual", "from": previous, "to": classification.value},
        )
        await self.db.commit()
        result = await self.messages.get_by_id(message.id, organization_id)
        assert result is not None
        return result

    async def _apply_classification_side_effects(
        self, lead: Lead, classification: ReplyClassificationEnum, actor: User
    ) -> None:
        if classification in (ReplyClassificationEnum.INTERESTED, ReplyClassificationEnum.MEETING_REQUESTED):
            new_status = next_lead_status(lead.status, LeadStatusEnum.INTERESTED)
            if new_status != lead.status:
                await self.lead_service.update(lead, payload=LeadUpdateRequest(status=new_status), actor=actor)
        elif classification == ReplyClassificationEnum.UNSUBSCRIBE_REQUEST:
            await suppress_lead(
                self.db, lead, status=LeadStatusEnum.UNSUBSCRIBED, audit_event="lead_auto_suppressed",
                actor=actor, extra_changes={"reason": "unsubscribe_request_reply"},
            )
        elif classification in _REPLIED_ONLY_CLASSIFICATIONS:
            pass  # explicitly no additional status change beyond the REPLIED transition already applied at ingest time

    # ─── Read paths ─────────────────────────────────────────────────────────────

    async def require_conversation(self, conversation_id: uuid.UUID, organization_id: uuid.UUID) -> Conversation:
        conversation = await self.conversations.get_by_id(conversation_id, organization_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation

    async def require_message(self, message_id: uuid.UUID, organization_id: uuid.UUID) -> Message:
        message = await self.messages.get_by_id(message_id, organization_id)
        if message is None:
            raise NotFoundError("Message not found.")
        return message

    async def mark_conversation_read(
        self, organization_id: uuid.UUID, conversation_id: uuid.UUID, *, is_read: bool
    ) -> Conversation:
        conversation = await self.require_conversation(conversation_id, organization_id)
        for message in conversation.messages:
            if message.is_read != is_read:
                message.is_read = is_read
        await self.db.commit()
        return await self.require_conversation(conversation_id, organization_id)
