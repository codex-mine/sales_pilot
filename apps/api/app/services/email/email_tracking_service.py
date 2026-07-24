"""
Communication -> Email Open/Click Tracking & Delivery Events.

The append-only ingestion layer for `EmailEvent` — the canonical source of
truth for delivery/engagement state per the model docstring on `Email`:
"We never update Email.status directly after send — we derive the current
status from the most recent EmailEvent." Every event-recording path here
(pixel, click, webhook) is the ONLY code that writes `Email.current_status`,
and always through `email_status_resolver.next_status(...)` so "never move
status backwards" lives in exactly one place.

This module never sends anything — it only observes what happens to emails
`EmailSendingService` (module 07) already sent.
"""

import secrets
import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from user_agents import parse as parse_user_agent

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError, ValidationError
from app.models.communication.models import Email, EmailEvent
from app.models.enums import ActivityTypeEnum, AuditActionEnum, EmailEventTypeEnum, LeadStatusEnum, NotificationTypeEnum
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_event_repository import EmailEventRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.email_template_repository import EmailTemplateRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.leads import LeadUpdateRequest
from app.security.tokens import sign_click_url, verify_click_signature
from app.services.email.email_status_resolver import next_status
from app.services.lead_service import LeadService
from app.services.lead_status_resolver import next_lead_status
from app.services.lead_suppression import suppress_lead
from app.services.system_actor import resolve_org_owner


# Substrings identifying a scanner/prefetch/automated client rather than a
# real mail client's rendering engine — combined with fast-after-send
# timing to flag likely-bot opens (see `_is_likely_bot_open`).
_PREFETCH_UA_MARKERS = (
    "bot", "crawler", "spider", "scanner", "prefetch", "proxy",
    "python-requests", "curl/", "wget", "go-http-client", "headlesschrome",
)

# 1x1 transparent PNG, served byte-for-byte identical on every request.
TRACKING_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6360000002000155"
    "0087eb4a8d0000000049454e44ae426082"
)


@dataclass
class OpenResult:
    was_recorded: bool
    was_bot_flagged: bool


class EmailTrackingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.emails = EmailRepository(db)
        self.events = EmailEventRepository(db)
        self.leads = LeadRepository(db)
        self.templates = EmailTemplateRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.lead_service = LeadService(db)
        self.notifications = NotificationRepository(db)

    # ─── Send-time instrumentation (called from EmailSendingService) ───────────

    async def instrument_content(
        self, email: Email, body_html: str, body_text: str, unsubscribe_url: str, *, include_open_pixel: bool = True
    ) -> tuple[str, str]:
        """Rewrites every link except the unsubscribe link to route through
        the click-tracking redirect, and appends the open-tracking pixel.
        Generates and persists `Email.tracking_pixel_id` first if module 07
        hasn't set one yet — tracking owns this field, per the module spec's
        own coordination note.

        `include_open_pixel=False` is used by `EmailSendingService.preview()`:
        a preview is rendered in the sender's own browser, which would fetch
        a live `<img>` pixel immediately and falsely record a real "opened"
        event before the email has even reached the recipient."""
        if not email.tracking_pixel_id:
            email.tracking_pixel_id = secrets.token_urlsafe(24)
            await self.db.flush()

        settings = get_settings()
        pixel_id = email.tracking_pixel_id

        instrumented_html = body_html
        if email.is_click_tracked:
            soup = BeautifulSoup(body_html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                if href == unsubscribe_url or not href.startswith(("http://", "https://")):
                    continue
                signature = sign_click_url(pixel_id, href)
                redirect_url = (
                    f"{settings.api_base_url}/api/v1/track/click/{pixel_id}"
                    f"?url={urllib.parse.quote(href, safe='')}&sig={signature}"
                )
                anchor["href"] = redirect_url
            instrumented_html = str(soup)

        if email.is_open_tracked and include_open_pixel:
            pixel_url = f"{settings.api_base_url}/api/v1/track/open/{pixel_id}.png"
            pixel_tag = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;" />'
            instrumented_html = f"{instrumented_html}{pixel_tag}"

        return instrumented_html, body_text

    async def record_sent(self, email: Email) -> None:
        """Called by `EmailSendingService` immediately after a successful
        dispatch. `Email.current_status` is already "sent" by the time this
        runs (the sending module owns that transition) — this only appends
        the corresponding `EmailEvent` row so `total_sent`/open-rate/
        click-rate denominators in analytics have something to divide by."""
        await self.events.create(
            organization_id=email.organization_id, email_id=email.id,
            event_type=EmailEventTypeEnum.SENT.value, occurred_at=datetime.now(timezone.utc),
        )
        await self.db.commit()

    # ─── Open tracking ──────────────────────────────────────────────────────────

    async def record_open(self, tracking_pixel_id: str, *, ip_address: str | None, user_agent: str | None) -> None:
        """Never raises — an invalid/unknown pixel id is a silent no-op so
        the pixel response is never delayed or errored by a lookup miss."""
        email = await self.emails.get_by_tracking_pixel_id(tracking_pixel_id)
        if email is None or not email.is_open_tracked:
            return

        now = datetime.now(timezone.utc)
        settings = get_settings()
        dedupe_since = now - timedelta(seconds=settings.email_open_dedupe_window_seconds)
        if await self.events.get_recent_open(email.id, dedupe_since) is not None:
            return  # repeated fire within the dedupe window — not a new event

        is_bot = self._is_likely_bot_open(email, user_agent, now)
        await self.events.create(
            organization_id=email.organization_id, email_id=email.id, event_type=EmailEventTypeEnum.OPENED.value,
            occurred_at=now, ip_address=ip_address, user_agent=user_agent,
            metadata_={"likely_bot": is_bot} if is_bot else None,
        )
        await self.db.commit()

        if is_bot:
            return  # recorded for the record, but must not drive status/metrics

        await self._apply_engagement_event(email, EmailEventTypeEnum.OPENED, ActivityTypeEnum.EMAIL_OPENED)

    def _is_likely_bot_open(self, email: Email, user_agent: str | None, now: datetime) -> bool:
        """Per the module's own heuristic, fast-after-send timing ALONE is
        not sufficient evidence (a genuine human can open within seconds) —
        only flagged when the timing is implausibly fast AND the UA itself
        looks like a scanner/prefetch client rather than a real mail
        client's browser engine. A recognizable bot/crawler UA is suspicious
        on its own, regardless of timing."""
        if not user_agent:
            return True  # no UA at all doesn't look like a real mail client fetch either

        ua_lower = user_agent.lower()
        is_suspicious_ua = any(marker in ua_lower for marker in _PREFETCH_UA_MARKERS)
        if not is_suspicious_ua:
            try:
                is_suspicious_ua = parse_user_agent(user_agent).is_bot
            except Exception:  # noqa: BLE001 — a malformed UA string is not itself bot evidence
                pass

        if not is_suspicious_ua:
            return False
        if not email.sent_at:
            return is_suspicious_ua  # no timing signal to corroborate — the UA alone already looks like a crawler

        window = timedelta(seconds=get_settings().email_open_bot_window_seconds)
        sent_at = email.sent_at if email.sent_at.tzinfo else email.sent_at.replace(tzinfo=timezone.utc)
        return (now - sent_at) <= window

    # ─── Click tracking ─────────────────────────────────────────────────────────

    async def resolve_click(
        self, tracking_pixel_id: str, url: str, signature: str, *, ip_address: str | None, user_agent: str | None
    ) -> str:
        """Always returns a safe URL to redirect to — an invalid signature
        or unknown pixel id redirects to the platform default rather than
        ever following an unsigned target (this endpoint must never become
        an open redirector)."""
        settings = get_settings()
        safe_default = settings.frontend_url

        if not verify_click_signature(tracking_pixel_id, url, signature):
            return safe_default

        email = await self.emails.get_by_tracking_pixel_id(tracking_pixel_id)
        if email is None:
            return safe_default

        now = datetime.now(timezone.utc)
        is_bot = self._is_likely_bot_open(email, user_agent, now)
        await self.events.create(
            organization_id=email.organization_id, email_id=email.id, event_type=EmailEventTypeEnum.CLICKED.value,
            occurred_at=now, ip_address=ip_address, user_agent=user_agent, click_url=url,
            metadata_={"likely_bot": is_bot} if is_bot else None,
        )
        # A click implies an open — backfill one if none exists yet (some
        # clients block images but allow clicks).
        dedupe_since = now - timedelta(seconds=settings.email_open_dedupe_window_seconds)
        if await self.events.get_recent_open(email.id, dedupe_since) is None:
            await self.events.create(
                organization_id=email.organization_id, email_id=email.id, event_type=EmailEventTypeEnum.OPENED.value,
                occurred_at=now, ip_address=ip_address, user_agent=user_agent,
                metadata_={"likely_bot": is_bot, "backfilled_from_click": True} if is_bot else {"backfilled_from_click": True},
            )
        await self.db.commit()

        if not is_bot:
            await self._apply_engagement_event(email, EmailEventTypeEnum.CLICKED, ActivityTypeEnum.EMAIL_CLICKED)

        return url

    # ─── Shared engagement side effects (open/click) ───────────────────────────

    async def _apply_engagement_event(
        self, email: Email, event_type: EmailEventTypeEnum, activity_type: ActivityTypeEnum
    ) -> None:
        fresh_email = await self.emails.get_by_id(email.id, email.organization_id)
        if fresh_email is None:
            return
        new_status = next_status(fresh_email.current_status, event_type)
        if new_status != fresh_email.current_status:
            fresh_email.current_status = new_status
            await self.db.flush()

        lead = await self.leads.get_by_id(fresh_email.lead_id, fresh_email.organization_id)
        if lead is None:
            await self.db.commit()
            return

        try:
            actor = await resolve_org_owner(self.db, fresh_email.organization_id)
        except NotFoundError:
            actor = None

        if actor is not None and event_type == EmailEventTypeEnum.OPENED:
            new_lead_status = next_lead_status(lead.status, LeadStatusEnum.OPENED)
            if new_lead_status != lead.status:
                await self.lead_service.update(
                    lead, payload=LeadUpdateRequest(status=new_lead_status), actor=actor
                )

        if event_type == EmailEventTypeEnum.OPENED and lead.owner_id:
            await self.notifications.create(
                organization_id=fresh_email.organization_id, user_id=lead.owner_id,
                notification_type=NotificationTypeEnum.EMAIL_OPENED.value,
                title="Email opened",
                body=f"{lead.full_name} opened your email.",
                entity_type="email", entity_id=fresh_email.id, action_url=f"/leads/{lead.id}",
            )

        if actor is not None:
            await self.activities.record(
                organization_id=fresh_email.organization_id, lead_id=lead.id, actor_id=None,
                activity_type=activity_type,
                summary=f"{lead.full_name} {'opened' if event_type == EmailEventTypeEnum.OPENED else 'clicked'} an email",
            )

        if fresh_email.email_template_id and event_type == EmailEventTypeEnum.OPENED:
            template = await self.templates.get_by_id(fresh_email.email_template_id, fresh_email.organization_id)
            if template is not None:
                template.total_opened += 1
                await self.db.flush()

        await self.db.commit()

    # ─── Delivery / bounce / complaint webhook ─────────────────────────────────

    async def ingest_webhook_event(self, provider: str, payload: dict) -> None:
        """Caller (the route) must have already verified the webhook
        signature — this trusts `payload` completely."""
        event_type_raw = payload.get("event_type")
        message_id = payload.get("message_id")
        provider_event_id = payload.get("event_id")
        if not event_type_raw or not message_id or not provider_event_id:
            raise ValidationError("Webhook payload missing event_type, message_id, or event_id.")
        try:
            event_type = EmailEventTypeEnum(event_type_raw)
        except ValueError as exc:
            raise ValidationError(f"Unknown event_type: '{event_type_raw}'.") from exc

        email = await self.emails.get_by_external_message_id(message_id)
        if email is None:
            return  # nothing to attach this to — silently accepted, matches webhook idempotency expectations

        occurred_at = self._parse_timestamp(payload.get("timestamp"))
        bounce_type = payload.get("bounce_type")
        reason = payload.get("reason")

        event, was_created = await self.events.create_idempotent_by_provider_event_id(
            organization_id=email.organization_id, email_id=email.id, event_type=event_type.value,
            provider_event_id=provider_event_id, provider=provider, occurred_at=occurred_at,
            bounce_reason=reason, metadata_={"bounce_type": bounce_type} if bounce_type else None,
        )
        if not was_created:
            return  # redelivered webhook — already processed

        await self.db.commit()

        if event_type == EmailEventTypeEnum.DELIVERED:
            await self._advance_status_only(email, event_type)
        elif event_type == EmailEventTypeEnum.BOUNCED:
            await self._handle_bounce(email, bounce_type=bounce_type, reason=reason)
        elif event_type == EmailEventTypeEnum.COMPLAINED:
            await self._handle_complaint(email)
        elif event_type == EmailEventTypeEnum.FAILED:
            await self._advance_status_only(email, event_type)

    def _parse_timestamp(self, raw: str | None) -> datetime:
        if not raw:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)

    async def _advance_status_only(self, email: Email, event_type: EmailEventTypeEnum) -> None:
        fresh_email = await self.emails.get_by_id(email.id, email.organization_id)
        if fresh_email is None:
            return
        new_status = next_status(fresh_email.current_status, event_type)
        if new_status != fresh_email.current_status:
            fresh_email.current_status = new_status
            await self.db.commit()

    async def _handle_bounce(self, email: Email, *, bounce_type: str | None, reason: str | None) -> None:
        is_hard = (bounce_type or "").lower() == "hard"
        await self._advance_status_only(email, EmailEventTypeEnum.BOUNCED)

        try:
            actor = await resolve_org_owner(self.db, email.organization_id)
        except NotFoundError:
            actor = None

        severity = "hard" if is_hard else "soft"
        await self.audit_log.record(
            organization_id=email.organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": f"email_bounced_{severity}", "reason": reason},
        )

        if is_hard and actor is not None:
            lead = await self.leads.get_by_id(email.lead_id, email.organization_id)
            if lead is not None:
                await suppress_lead(
                    self.db, lead, status=LeadStatusEnum.BOUNCED,
                    audit_event="lead_auto_suppressed", actor=actor, extra_changes={"reason": "hard_bounce"},
                )
        await self.db.commit()

    async def _handle_complaint(self, email: Email) -> None:
        await self._advance_status_only(email, EmailEventTypeEnum.COMPLAINED)

        try:
            actor = await resolve_org_owner(self.db, email.organization_id)
        except NotFoundError:
            actor = None

        await self.audit_log.record(
            organization_id=email.organization_id, actor_id=None, actor_email=None,
            action=AuditActionEnum.UPDATE, resource_type="email", resource_id=email.id,
            changes={"event": "email_complained"},
        )

        if actor is not None:
            lead = await self.leads.get_by_id(email.lead_id, email.organization_id)
            if lead is not None:
                # Distinct audit reason from "unsubscribe_processed" (module
                # 07) — a spam complaint is not a self-service unsubscribe
                # click, and the two must stay tellable-apart in the trail.
                await suppress_lead(
                    self.db, lead, status=LeadStatusEnum.UNSUBSCRIBED,
                    audit_event="lead_auto_suppressed", actor=actor, extra_changes={"reason": "spam_complaint"},
                )
        await self.db.commit()

    # ─── Read paths ─────────────────────────────────────────────────────────────

    async def require_email(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> Email:
        email = await self.emails.get_by_id(email_id, organization_id)
        if email is None:
            raise NotFoundError("Email not found.")
        return email

    async def get_events(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> list[EmailEvent]:
        await self.require_email(email_id, organization_id)
        return await self.events.list_for_email(email_id, organization_id)

    async def get_timeline(self, email_id: uuid.UUID, organization_id: uuid.UUID) -> dict:
        email = await self.require_email(email_id, organization_id)
        events = await self.events.list_for_email(email_id, organization_id)
        return {"email_id": str(email.id), "current_status": email.current_status, "events": events}

    async def get_performance_analytics(self, organization_id: uuid.UUID, *, days: int = 30) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        counts = await self.events.aggregate_counts(organization_id, since=since)
        sent = counts.get(EmailEventTypeEnum.SENT.value, 0)
        delivered = counts.get(EmailEventTypeEnum.DELIVERED.value, 0)
        opened = counts.get(EmailEventTypeEnum.OPENED.value, 0)
        clicked = counts.get(EmailEventTypeEnum.CLICKED.value, 0)
        bounced = counts.get(EmailEventTypeEnum.BOUNCED.value, 0)
        complained = counts.get(EmailEventTypeEnum.COMPLAINED.value, 0)
        denominator = delivered or sent or 1

        daily_raw = await self.events.daily_counts(organization_id, since=since)
        daily = []
        for day in sorted(daily_raw):
            day_counts = daily_raw[day]
            d_sent = day_counts.get(EmailEventTypeEnum.SENT.value, 0)
            d_delivered = day_counts.get(EmailEventTypeEnum.DELIVERED.value, 0)
            d_opened = day_counts.get(EmailEventTypeEnum.OPENED.value, 0)
            d_clicked = day_counts.get(EmailEventTypeEnum.CLICKED.value, 0)
            d_bounced = day_counts.get(EmailEventTypeEnum.BOUNCED.value, 0)
            d_denominator = d_delivered or d_sent or 1
            daily.append(
                {
                    "date": day.date().isoformat(),
                    "sent": d_sent, "delivered": d_delivered, "opened": d_opened,
                    "clicked": d_clicked, "bounced": d_bounced,
                    "open_rate": round(d_opened / d_denominator, 4) if (d_delivered or d_sent) else 0.0,
                    "click_rate": round(d_clicked / d_denominator, 4) if (d_delivered or d_sent) else 0.0,
                    "bounce_rate": round(d_bounced / d_sent, 4) if d_sent else 0.0,
                }
            )

        return {
            "window_days": days,
            "total_sent": sent,
            "total_delivered": delivered,
            "total_opened": opened,
            "total_clicked": clicked,
            "total_bounced": bounced,
            "total_complained": complained,
            "open_rate": round(opened / denominator, 4) if (delivered or sent) else 0.0,
            "click_rate": round(clicked / denominator, 4) if (delivered or sent) else 0.0,
            "bounce_rate": round(bounced / (sent or 1), 4) if sent else 0.0,
            "daily": daily,
        }
