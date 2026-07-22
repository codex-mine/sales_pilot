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
import socket
import ssl
import uuid
from abc import ABC, abstractmethod
from asyncio import to_thread
from dataclasses import dataclass, field
from email.message import EmailMessage

from app.exceptions.errors import EmailSendError, ValidationError


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


def _connect(host: str, port: int, encryption_type: str, timeout: int = 15) -> smtplib.SMTP:
    """`encryption_type`: "ssl" connects with implicit TLS from the start
    (`smtplib.SMTP_SSL`, typically port 465); "starttls" connects plain then
    upgrades (typically port 587); "none" stays plain throughout."""
    if encryption_type == "ssl":
        return smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context())
    smtp = smtplib.SMTP(host, port, timeout=timeout)
    if encryption_type == "starttls":
        smtp.starttls(context=ssl.create_default_context())
    return smtp


class SMTPSenderClient(EmailSenderClient):
    def __init__(
        self, *, host: str, port: int, username: str | None, password: str | None, use_tls: bool,
        encryption_type: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        # `encryption_type` (from a per-mailbox config) takes precedence when
        # given; `use_tls` (the original, still-supported single-mailbox
        # shape) maps 1:1 onto "starttls"/"none" for backward compatibility.
        self.encryption_type = encryption_type or ("starttls" if use_tls else "none")

    def _send_sync(self, message: EmailMessage) -> None:
        with _connect(self.host, self.port, self.encryption_type) as smtp:
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
    provider: str, *, host: str, port: int, username: str | None, password: str | None, use_tls: bool,
    encryption_type: str | None = None,
) -> EmailSenderClient:
    """The single point of sender-provider branching. Today only "smtp" is
    implemented; Gmail/Outlook OAuth-based clients (see
    `IntegrationTypeEnum.GMAIL`/`OUTLOOK_EMAIL`) can be added here later
    without touching `EmailSendingService`."""
    if provider == "smtp":
        if not host:
            raise EmailSendError("No outreach sending mailbox is configured for this organization.")
        return SMTPSenderClient(
            host=host, port=port, username=username, password=password, use_tls=use_tls,
            encryption_type=encryption_type,
        )
    raise EmailSendError(f"Unsupported email sender provider: '{provider}'.")


# ─── Connection test (Sender Mailbox Management — verify before saving) ──────────


def _test_connection_sync(*, host: str, port: int, username: str | None, password: str, encryption_type: str) -> None:
    with _connect(host, port, encryption_type, timeout=10) as smtp:
        if username:
            smtp.login(username, password)
        # "Send a lightweight test request" — a NOOP round-trip after auth,
        # not an actual email, confirms the session is genuinely usable.
        smtp.noop()


async def test_smtp_connection(
    *, host: str, port: int, username: str | None, password: str, encryption_type: str
) -> None:
    """Raises `ValidationError` with a clear, specific reason on any failure;
    returns normally on success. Never persists anything — purely a
    connect-and-verify probe, called before a mailbox is saved."""
    try:
        await to_thread(
            _test_connection_sync, host=host, port=port, username=username, password=password,
            encryption_type=encryption_type,
        )
    except smtplib.SMTPAuthenticationError as exc:
        raise ValidationError(f"Authentication failed: {exc.smtp_error.decode(errors='replace') if exc.smtp_error else exc}") from exc
    except smtplib.SMTPConnectError as exc:
        raise ValidationError(f"Could not connect to SMTP host: {exc}") from exc
    except smtplib.SMTPServerDisconnected as exc:
        raise ValidationError(f"SMTP server disconnected unexpectedly: {exc}") from exc
    except smtplib.SMTPNotSupportedError as exc:
        raise ValidationError(f"Requested encryption is not supported by this server: {exc}") from exc
    except ssl.SSLError as exc:
        raise ValidationError(f"SSL error: {exc}") from exc
    except socket.gaierror as exc:
        raise ValidationError(f"Invalid SMTP host — could not resolve '{host}': {exc}") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise ValidationError(f"Connection timed out: {exc}") from exc
    except ConnectionRefusedError as exc:
        raise ValidationError(f"Connection refused by host — check the host and port: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise ValidationError(f"SMTP error: {exc}") from exc
    except OSError as exc:
        raise ValidationError(f"Connection failed: {exc}") from exc
