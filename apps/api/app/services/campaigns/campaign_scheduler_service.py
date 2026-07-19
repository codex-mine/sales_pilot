"""
Campaigns -> the sequence-execution engine. `execute_step` is the worker
task's entry point (one CampaignLead at a time); `advance_after_send` is the
shared "compute the next step" helper called both from the automation send
path here AND from `EmailSendingService._attempt_send`'s success hook when a
sequence-linked Draft is manually approved-then-sent — both converge on the
same logic instead of duplicating it, per the module spec.

Orchestration only: generation goes through `EmailGenerationService`, sending
through `EmailSendingService`, engagement checks through
`email_status_resolver`/`lead_status_resolver` — nothing here reimplements
any of that.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, Undefined
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIOutput
from app.models.campaigns.models import Campaign, CampaignLead, SequenceStep
from app.models.communication.models import Email
from app.models.crm.models import Lead
from app.models.enums import (
    ActivityTypeEnum,
    AIJobStatusEnum,
    AuditActionEnum,
    CampaignLeadStatusEnum,
    CampaignStatusEnum,
    EmailStatusEnum,
    EmailTemplateTypeEnum,
    EmailToneEnum,
    LeadStatusEnum,
    NotificationTypeEnum,
    SequenceStepTypeEnum,
)
from app.repositories.activity_repository import ActivityRepository
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.ai_output_repository import AIOutputRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.campaign_lead_repository import CampaignLeadRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.sequence_repository import SequenceRepository
from app.services.ai.email_generation_service import EmailGenerationService
from app.services.campaigns.campaign_settings import get_requires_approval
from app.services.campaigns.send_window import roll_forward_into_window
from app.services.campaigns.sequence_service import split_condition
from app.services.email import email_status_resolver
from app.services.email.email_sending_service import EmailSendingService
from app.services.lead_status_resolver import has_reached as lead_has_reached
from app.services.system_actor import resolve_org_owner

_ACTIVE_CAMPAIGN_LEAD_STATUSES = {CampaignLeadStatusEnum.ENROLLED.value, CampaignLeadStatusEnum.IN_PROGRESS.value}
_ENGAGEMENT_MILESTONES: dict[str, EmailStatusEnum] = {
    "sent": EmailStatusEnum.SENT,
    "delivered": EmailStatusEnum.DELIVERED,
    "opened": EmailStatusEnum.OPENED,
    "clicked": EmailStatusEnum.CLICKED,
}


class CampaignSchedulerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaign_leads = CampaignLeadRepository(db)
        self.sequences = SequenceRepository(db)
        self.campaigns = CampaignRepository(db)
        self.leads = LeadRepository(db)
        self.emails = EmailRepository(db)
        self.ai_jobs = AIJobRepository(db)
        self.ai_outputs = AIOutputRepository(db)
        self.notifications = NotificationRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.email_generation = EmailGenerationService(db)
        self.email_sending = EmailSendingService(db)

    # ─── Entry point (worker task) ─────────────────────────────────────────────

    async def execute_step(self, campaign_lead_id: uuid.UUID) -> None:
        campaign_lead = await self.campaign_leads.get_for_processing(campaign_lead_id)
        if campaign_lead is None or campaign_lead.status not in _ACTIVE_CAMPAIGN_LEAD_STATUSES:
            return  # already terminal/paused, or the row vanished — safe no-op

        lead = campaign_lead.lead
        campaign = campaign_lead.campaign
        if lead is None or campaign is None:
            return

        if await self._auto_stop_if_needed(campaign_lead, lead):
            return

        if campaign.status != CampaignStatusEnum.ACTIVE.value:
            # Paused/archived mid-flight: leave next_action_at cleared (the
            # claim already cleared it) so it's not picked up again until
            # `CampaignService.activate()` explicitly re-primes it.
            return

        step = campaign_lead.next_step
        if step is None:
            await self._complete(campaign_lead, campaign)
            return

        rules, content_source = split_condition(step.condition)
        if await self._should_skip(rules, lead, campaign):
            await self._advance_to_next_step(campaign_lead, step, campaign)
            return

        if step.step_type == SequenceStepTypeEnum.WAIT.value:
            await self._advance_to_next_step(campaign_lead, step, campaign)
        elif step.step_type == SequenceStepTypeEnum.TASK.value:
            await self._execute_task_step(campaign, lead, step)
            await self._advance_to_next_step(campaign_lead, step, campaign)
        elif step.step_type == SequenceStepTypeEnum.EMAIL.value:
            await self._execute_email_step(campaign_lead, step, lead, campaign, content_source)
        else:
            # Unsupported types are rejected at creation time — defensive
            # fallback only, never reached in practice.
            await self._advance_to_next_step(campaign_lead, step, campaign)

    # ─── Auto-stop ──────────────────────────────────────────────────────────────

    async def _auto_stop_if_needed(self, campaign_lead: CampaignLead, lead: Lead) -> bool:
        """The single most important correctness rule in this module: never
        touch a lead again once they've replied, unsubscribed, bounced, or
        already booked a meeting. Checked first, before anything else."""
        new_status: CampaignLeadStatusEnum | None = None
        if lead.status == LeadStatusEnum.UNSUBSCRIBED.value:
            new_status = CampaignLeadStatusEnum.OPTED_OUT
        elif lead.status == LeadStatusEnum.BOUNCED.value:
            new_status = CampaignLeadStatusEnum.BOUNCED
        elif lead_has_reached(lead.status, LeadStatusEnum.DEMO_SCHEDULED):
            new_status = CampaignLeadStatusEnum.MEETING_BOOKED
        elif lead_has_reached(lead.status, LeadStatusEnum.REPLIED):
            new_status = CampaignLeadStatusEnum.REPLIED

        if new_status is None:
            return False

        await self.campaign_leads.update(
            campaign_lead,
            {"status": new_status.value, "completed_at": datetime.now(timezone.utc), "next_action_at": None},
        )
        await self.activities.record(
            organization_id=campaign_lead.organization_id, lead_id=lead.id, actor_id=None,
            activity_type=ActivityTypeEnum.BULK_ACTION,
            summary=f"Sequence auto-stopped ({new_status.value}) for {lead.full_name}",
        )
        await self.db.commit()
        return True

    # ─── Conditional skip ───────────────────────────────────────────────────────

    async def _should_skip(self, rules: dict, lead: Lead, campaign: Campaign) -> bool:
        skip_if = rules.get("skip_if")
        only_if = rules.get("only_if")
        if not skip_if and not only_if:
            return False

        latest_email = await self.emails.get_latest_for_lead_in_campaign(lead.id, campaign.id)

        def _reached(milestone_key: str) -> bool:
            if milestone_key == "replied":
                return lead_has_reached(lead.status, LeadStatusEnum.REPLIED)
            email_milestone = _ENGAGEMENT_MILESTONES.get(milestone_key)
            if email_milestone is None or latest_email is None:
                return False
            return email_status_resolver.has_reached(latest_email.current_status, email_milestone)

        if skip_if and _reached(skip_if):
            return True
        if only_if and not _reached(only_if):
            return True
        return False

    # ─── Step execution ─────────────────────────────────────────────────────────

    async def _execute_task_step(self, campaign: Campaign, lead: Lead, step: SequenceStep) -> None:
        """No Task domain exists in this schema — a Notification stands in
        for a reminder, per the module spec's explicit scope call."""
        owner_id = lead.owner_id or campaign.owner_id
        if owner_id is None:
            return
        await self.notifications.create(
            organization_id=campaign.organization_id, user_id=owner_id,
            notification_type=NotificationTypeEnum.SYSTEM.value,
            title=f"Campaign task: {campaign.name}",
            body=f"A task step is due for {lead.full_name} in '{campaign.name}'.",
            entity_type="lead", entity_id=lead.id, action_url=f"/leads/{lead.id}",
        )

    async def _execute_email_step(
        self, campaign_lead: CampaignLead, step: SequenceStep, lead: Lead, campaign: Campaign, content_source: str
    ) -> None:
        if not lead.email:
            await self.audit_log.record(
                organization_id=campaign.organization_id, actor_id=None, actor_email=None,
                action=AuditActionEnum.UPDATE, resource_type="campaign_lead", resource_id=campaign_lead.id,
                changes={"event": "campaign_step_skipped_no_email", "lead_id": str(lead.id)},
            )
            await self.db.commit()
            return  # stalled: next_action_at stays cleared until manually re-enrolled/fixed

        sent_today = await self.emails.count_sent_today_for_campaign(campaign.id)
        if sent_today >= campaign.daily_send_limit:
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            next_slot = roll_forward_into_window(
                tomorrow, send_days=campaign.send_days, send_start_hour=campaign.send_start_hour,
                send_end_hour=campaign.send_end_hour, tz_name=campaign.timezone,
            )
            await self.campaign_leads.update(
                campaign_lead, {"status": CampaignLeadStatusEnum.IN_PROGRESS.value, "next_action_at": next_slot}
            )
            await self.db.commit()
            return

        actor = await resolve_org_owner(self.db, campaign.organization_id)
        from_email = campaign.owner.email if campaign.owner else actor.email
        from_name = campaign.owner.full_name if campaign.owner else actor.full_name

        if content_source == "ai_personalized":
            email = await self._generate_ai_email(campaign_lead, lead, campaign, actor=actor,
                                                    from_email=from_email, from_name=from_name)
        else:
            email = await self._create_email_from_template(campaign_lead, step, lead, campaign,
                                                              from_email=from_email, from_name=from_name)
        if email is None:
            return  # generation/template failure already logged by the callee

        await self.emails.update(email, {"campaign_lead_id": campaign_lead.id, "sequence_step_id": step.id})
        await self.db.commit()

        if get_requires_approval(campaign):
            owner_id = lead.owner_id or campaign.owner_id
            if owner_id:
                await self.notifications.create(
                    organization_id=campaign.organization_id, user_id=owner_id,
                    notification_type=NotificationTypeEnum.AI_EMAIL_GENERATED.value,
                    title="Sequence email awaiting approval",
                    body=f"A draft for {lead.full_name} in '{campaign.name}' is ready to review.",
                    entity_type="email", entity_id=email.id, action_url=f"/leads/{lead.id}",
                )
            await self.campaign_leads.update(
                campaign_lead, {"status": CampaignLeadStatusEnum.IN_PROGRESS.value, "next_action_at": None}
            )
            await self.db.commit()
            # Stalled by design until a human approves & sends the Draft —
            # `EmailSendingService._attempt_send`'s success hook calls
            # `advance_after_send` at that point, resuming the sequence.
            return

        try:
            await self.email_sending.send_now(campaign.organization_id, email.id, actor=actor)
        except Exception:  # noqa: BLE001 — a suppressed/failed send stalls this lead; _attempt_send already recorded why
            return
        # On success, `_attempt_send`'s hook already called `advance_after_send` — nothing more to do here.

    async def _create_email_from_template(
        self, campaign_lead: CampaignLead, step: SequenceStep, lead: Lead, campaign: Campaign,
        *, from_email: str, from_name: str,
    ) -> Email | None:
        template = step.email_template
        if template is None:
            await self.audit_log.record(
                organization_id=campaign.organization_id, actor_id=None, actor_email=None,
                action=AuditActionEnum.UPDATE, resource_type="campaign_lead", resource_id=campaign_lead.id,
                changes={"event": "campaign_step_missing_template", "step_id": str(step.id)},
            )
            await self.db.commit()
            return None

        variables = _render_context(lead)
        subject = step.subject_override or _render(template.subject, variables)
        body_html = step.body_override or _render(template.body_html, variables)
        body_text = _render(template.body_text, variables) if template.body_text else None

        email = await self.emails.create(
            organization_id=campaign.organization_id, lead_id=lead.id,
            from_email=from_email, from_name=from_name, to_email=lead.email, to_name=lead.full_name,
            subject=subject, body_html=body_html, body_text=body_text,
            current_status=EmailStatusEnum.DRAFT.value, ai_generated=False, email_template_id=template.id,
        )
        await self.db.commit()
        return email

    async def _generate_ai_email(
        self, campaign_lead: CampaignLead, lead: Lead, campaign: Campaign,
        *, actor, from_email: str, from_name: str,
    ) -> Email | None:
        template_type = (
            EmailTemplateTypeEnum.COLD_OUTREACH if campaign_lead.current_step_order == 0
            else EmailTemplateTypeEnum.FOLLOW_UP
        )
        job = await self.email_generation.generate_email(
            campaign.organization_id, lead.id, actor=actor, template_type=template_type,
            tone=EmailToneEnum.PROFESSIONAL, variant_count=1,
        )
        output = await self._wait_for_variant(job.id, campaign.organization_id)
        if output is None:
            await self.audit_log.record(
                organization_id=campaign.organization_id, actor_id=None, actor_email=None,
                action=AuditActionEnum.UPDATE, resource_type="campaign_lead", resource_id=campaign_lead.id,
                changes={"event": "campaign_step_ai_generation_failed", "ai_job_id": str(job.id)},
            )
            await self.db.commit()
            return None

        return await self.email_generation.approve_variant(
            campaign.organization_id, output.id, actor=actor, from_email=from_email, from_name=from_name,
        )

    async def _wait_for_variant(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> AIOutput | None:
        """Polls for the AIOutput row rather than calling `EmailGenerationService.
        finalize()` itself — that would race the SAME job's own dispatched
        finalize task (see `generate_email`'s eager/async branch) into
        creating duplicate variants. Whichever path's `finalize()` runs, this
        just waits for its result."""
        settings = get_settings()
        timeout_seconds = settings.ai_job_timeout_seconds * (settings.ai_max_retries + 1) + 60
        deadline = time.monotonic() + timeout_seconds
        while True:
            output = await self.ai_outputs.get_latest_for_job(job_id, organization_id, output_type="email_variant")
            if output is not None:
                return output
            job = await self.ai_jobs.get_by_id(job_id, organization_id)
            if job is not None and job.status in (AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED):
                return None
            if time.monotonic() > deadline:
                return None
            await asyncio.sleep(2)

    # ─── Advance / complete ─────────────────────────────────────────────────────

    async def advance_after_send(self, campaign_lead_id: uuid.UUID) -> None:
        """Called both by this service's own automation send path (via the
        `_attempt_send` hook, same call stack) and externally by
        `EmailSendingService._attempt_send` when a sequence-linked Draft is
        manually approved and sent later — the single place "what's next"
        is computed, so both paths never drift apart."""
        campaign_lead = await self.campaign_leads.get_for_processing(campaign_lead_id)
        if campaign_lead is None or campaign_lead.next_step is None:
            return
        campaign = campaign_lead.campaign or await self.campaigns.get_by_id(
            campaign_lead.campaign_id, campaign_lead.organization_id
        )
        if campaign is None:
            return
        await self._advance_to_next_step(campaign_lead, campaign_lead.next_step, campaign)

    async def _advance_to_next_step(
        self, campaign_lead: CampaignLead, completed_step: SequenceStep, campaign: Campaign
    ) -> None:
        next_step = await self.sequences.get_next_step(completed_step.sequence_id, completed_step.step_order)
        if next_step is None:
            await self.campaign_leads.update(
                campaign_lead,
                {
                    "status": CampaignLeadStatusEnum.COMPLETED.value, "current_step_order": completed_step.step_order,
                    "next_step_id": None, "next_action_at": None, "completed_at": datetime.now(timezone.utc),
                },
            )
            await self.db.commit()
            await self._maybe_complete_campaign(campaign)
            return

        candidate = datetime.now(timezone.utc) + timedelta(days=next_step.delay_days, hours=next_step.delay_hours)
        run_at = roll_forward_into_window(
            candidate, send_days=campaign.send_days, send_start_hour=campaign.send_start_hour,
            send_end_hour=campaign.send_end_hour, tz_name=campaign.timezone,
        )
        await self.campaign_leads.update(
            campaign_lead,
            {
                "status": CampaignLeadStatusEnum.IN_PROGRESS.value, "current_step_order": completed_step.step_order,
                "next_step_id": next_step.id, "next_action_at": run_at,
            },
        )
        await self.db.commit()

    async def _complete(self, campaign_lead: CampaignLead, campaign: Campaign) -> None:
        await self.campaign_leads.update(
            campaign_lead,
            {
                "status": CampaignLeadStatusEnum.COMPLETED.value, "next_step_id": None,
                "next_action_at": None, "completed_at": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()
        await self._maybe_complete_campaign(campaign)

    async def _maybe_complete_campaign(self, campaign: Campaign) -> None:
        """Campaign.status auto-advances draft->active->...->completed once
        every enrolled lead has reached a terminal per-lead status — there is
        no explicit "complete" action in the API (only activate/pause/
        archive), so this is the only place COMPLETED is ever reached."""
        if campaign.status != CampaignStatusEnum.ACTIVE.value:
            return
        counts = await self.campaigns.funnel_counts(campaign.id)
        total = sum(counts.values())
        if total == 0:
            return
        non_terminal = sum(
            count for status, count in counts.items()
            if status in _ACTIVE_CAMPAIGN_LEAD_STATUSES
        )
        if non_terminal == 0:
            await self.campaigns.update(
                campaign, {"status": CampaignStatusEnum.COMPLETED.value, "completed_at": datetime.now(timezone.utc)},
                updated_by=None,
            )
            await self.db.commit()


def _render_context(lead: Lead) -> dict:
    return {
        "lead": {
            "first_name": lead.first_name or "", "last_name": lead.last_name or "",
            "full_name": lead.full_name, "job_title": lead.job_title or "",
            "email": lead.email or "", "company_name": lead.company_name or "",
        },
        "company": {
            "name": lead.company_name or "", "industry": lead.industry or "",
        },
    }


class _LenientUndefined(Undefined):
    def __str__(self) -> str:
        return ""


_jinja = Environment(undefined=_LenientUndefined, autoescape=False)


def _render(template_str: str | None, variables: dict) -> str:
    """Lenient rendering (missing variables render as empty, never raise) —
    unlike `PromptService.render_prompt`'s `StrictUndefined`, this runs
    unattended inside an automated sequence and must never crash a step over
    a lead missing an optional field."""
    if not template_str:
        return ""
    return _jinja.from_string(template_str).render(**variables)
