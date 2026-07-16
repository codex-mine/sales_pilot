"""
Transactional email delivery for the auth flows (verify-email, password
reset, organization invitations).

Deliberately built on the stdlib `smtplib`/`email` modules rather than a new
third-party dependency — this is a small, additive piece of infrastructure,
not a reason to grow the dependency surface. Sending happens in a worker
thread (`asyncio.to_thread`) since `smtplib` is synchronous and this runs
inside an async request handler.

When `settings.smtp_host` is unset (the local-dev default), `send_email`
logs the message and returns without raising — registration, resend, and
forgot-password flows must keep working even when no mail server is
configured. This mirrors the existing `debug_*_token` meta fields: SMTP is
the production delivery path, not a hard requirement for the flow to
function.
"""

import smtplib
from asyncio import to_thread
from email.message import EmailMessage

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


def _send_sync(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_email(*, to: str, subject: str, html_body: str, text_body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("email_not_sent_smtp_unconfigured", to=to, subject=subject)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        await to_thread(_send_sync, message)
        logger.info("email_sent", to=to, subject=subject)
    except (OSError, smtplib.SMTPException) as exc:
        # Email delivery failures must never break the auth flow that
        # triggered them (register/resend/forgot-password already succeeded
        # server-side) — log loudly and move on.
        logger.error("email_send_failed", to=to, subject=subject, error=str(exc))


def _wrapper(preheader: str, title: str, body_html: str, button_label: str, button_url: str) -> str:
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#FAFAF9;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <span style="display:none;max-height:0;overflow:hidden;">{preheader}</span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;">
      <tr><td align="center">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;overflow:hidden;">
          <tr><td style="padding:32px 32px 24px 32px;">
            <p style="margin:0 0 24px 0;font-size:20px;font-weight:700;color:#16A34A;">SalesPilot</p>
            <h1 style="margin:0 0 16px 0;font-size:20px;line-height:28px;color:#0F172A;">{title}</h1>
            <div style="font-size:14px;line-height:22px;color:#374151;">{body_html}</div>
            <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr><td style="border-radius:8px;background-color:#16A34A;">
                <a href="{button_url}" style="display:inline-block;padding:10px 20px;font-size:14px;font-weight:600;color:#FFFFFF;text-decoration:none;">{button_label}</a>
              </td></tr>
            </table>
            <p style="margin:24px 0 0 0;font-size:12px;line-height:18px;color:#9CA3AF;">
              If the button doesn't work, copy and paste this link into your browser:<br />
              <a href="{button_url}" style="color:#16A34A;">{button_url}</a>
            </p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


async def send_verification_email(*, to: str, first_name: str, token: str) -> None:
    settings = get_settings()
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    html = _wrapper(
        preheader="Verify your email to finish setting up your SalesPilot workspace.",
        title=f"Welcome, {first_name} — please verify your email",
        body_html=(
            "<p>Confirm your email address to activate your SalesPilot account. "
            "This link expires in "
            f"{settings.email_verification_token_expire_hours} hours.</p>"
        ),
        button_label="Verify email",
        button_url=verify_url,
    )
    text = (
        f"Welcome, {first_name} — please verify your email.\n\n"
        f"Verify your email: {verify_url}\n\n"
        f"This link expires in {settings.email_verification_token_expire_hours} hours."
    )
    await send_email(to=to, subject="Verify your email address", html_body=html, text_body=text)


async def send_password_reset_email(*, to: str, first_name: str, token: str) -> None:
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    html = _wrapper(
        preheader="Reset your SalesPilot password.",
        title=f"Hi {first_name}, reset your password",
        body_html=(
            "<p>We received a request to reset your password. If you didn't make this "
            "request, you can safely ignore this email. This link expires in "
            f"{settings.password_reset_token_expire_minutes} minutes.</p>"
        ),
        button_label="Reset password",
        button_url=reset_url,
    )
    text = (
        f"Hi {first_name}, reset your password.\n\n"
        f"Reset your password: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_token_expire_minutes} minutes."
    )
    await send_email(to=to, subject="Reset your password", html_body=html, text_body=text)


async def send_invitation_email(*, to: str, organization_name: str, token: str) -> None:
    settings = get_settings()
    accept_url = f"{settings.frontend_url}/accept-invitation?token={token}"
    html = _wrapper(
        preheader=f"You've been invited to join {organization_name} on SalesPilot.",
        title=f"You've been invited to join {organization_name}",
        body_html=(
            f"<p>You've been invited to join <strong>{organization_name}</strong> on "
            f"SalesPilot. This invitation expires in {settings.invitation_token_expire_days} days.</p>"
        ),
        button_label="Accept invitation",
        button_url=accept_url,
    )
    text = (
        f"You've been invited to join {organization_name} on SalesPilot.\n\n"
        f"Accept your invitation: {accept_url}\n\n"
        f"This invitation expires in {settings.invitation_token_expire_days} days."
    )
    await send_email(to=to, subject=f"You've been invited to join {organization_name}", html_body=html, text_body=text)
