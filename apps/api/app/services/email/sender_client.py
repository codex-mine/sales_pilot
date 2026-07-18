"""
Provider-agnostic email sender abstraction. Mirrors
`app.services.ai.llm_client` exactly — same shape, same reasoning: this is
the ONLY place a sender-provider SDK/protocol is spoken and where provider
branching happens; `EmailSendingService` calls
`get_sender_client(...).send(...)` and never touches SMTP/SDK details itself.

Built on the stdlib `smtplib`/`email` modules, matching
`app.services.email_service` (the transactional auth-email sender) rather
than introducing a second SMTP library — same reasoning: `smtplib` is
synchronous, so sending happens in a worker thread via `asyncio.to_thread`.

Every provider exception is caught and re-raised as `EmailSendError` so the
Email retry/failure path is uniform regardless of provider.
"""

import smtplib
import uuid
from abc import ABC, abstractmethod
from asyncio import to_thread
from dataclasses import dataclass, field
from email.message import EmailMessage

from app.exceptions.errors import EmailSendError


@dataclass
class SendResult:
    external_message_id: str
    raw_response: dict = field(default_factory=dict)


class EmailSenderClient(ABC):
    @abstractmethod
    async def send(
        self,
        *,
        from_email: str,
        from_name: str | None,
        to_email: str,
        to_name: str | None,
        reply_to: str | None,
        subject: str,
        body_html: str,
        body_text: str | None,
    ) -> SendResult: ...


def _build_message(
    *, from_email, from_name, to_email, to_name, reply_to, subject, body_html, body_text, message_id
) -> EmailMessage:
    message = EmailMessage()
    message["Message-ID"] = message_id
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body_text or "")
    message.add_alternative(body_html, subtype="html")
    return message


class SMTPSenderClient(EmailSenderClient):
    def __init__(self, *, host: str, port: int, username: str | None, password: str | None, use_tls: bool) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)

    async def send(
        self,
        *,
        from_email: str,
        from_name: str | None,
        to_email: str,
        to_name: str | None,
        reply_to: str | None,
        subject: str,
        body_html: str,
        body_text: str | None,
    ) -> SendResult:
        message_id = f"<{uuid.uuid4().hex}@{self.host}>"
        message = _build_message(
            from_email=from_email, from_name=from_name, to_email=to_email, to_name=to_name,
            reply_to=reply_to, subject=subject, body_html=body_html, body_text=body_text,
            message_id=message_id,
        )
        try:
            await to_thread(self._send_sync, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailSendError(f"SMTP send failed: {exc}") from exc
        return SendResult(external_message_id=message_id, raw_response={"host": self.host, "port": self.port})


def get_sender_client(
    provider: str, *, host: str, port: int, username: str | None, password: str | None, use_tls: bool
) -> EmailSenderClient:
    """The single point of sender-provider branching. Today only "smtp" is
    implemented; Gmail/Outlook OAuth-based clients (see
    `IntegrationTypeEnum.GMAIL`/`OUTLOOK_EMAIL`) can be added here later
    without touching `EmailSendingService`."""
    if provider == "smtp":
        if not host:
            raise EmailSendError("No outreach sending mailbox is configured for this organization.")
        return SMTPSenderClient(host=host, port=port, username=username, password=password, use_tls=use_tls)
    raise EmailSendError(f"Unsupported email sender provider: '{provider}'.")
