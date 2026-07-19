"""
Delivery-webhook signature verification, keyed by provider name.

`EmailSenderClient` (module 07) only implements plain SMTP today — no
specific ESP is wired — so there is no single "the" provider signature
scheme to implement. Rather than fake partial support for several providers
whose correctness can't be verified without their SDKs, this implements one
concrete, fully-correct scheme ("generic": HMAC-SHA256 over the raw request
body with a shared secret, matching how Mailgun/most webhook systems sign)
and rejects any other provider name outright. A real SendGrid/SES/Postmark
integration adds its own verifier function here, dispatched the same way —
this module is the only place that branches on provider name, mirroring
`sender_client.py`'s single-dispatch-point shape.
"""

import hashlib
import hmac

from app.core.config import get_settings


def _webhook_secret() -> str:
    settings = get_settings()
    if settings.email_webhook_signing_secret:
        return settings.email_webhook_signing_secret
    # Dev fallback: derive a stable secret from the JWT key, same pattern as
    # app/security/crypto.py's Fernet key derivation — never used once a
    # deployment sets EMAIL_WEBHOOK_SIGNING_SECRET explicitly.
    return hashlib.sha256(f"email-webhook:{settings.jwt_secret_key}".encode()).hexdigest()


def sign_generic_webhook(body: bytes) -> str:
    """The counterpart to `_verify_generic_hmac` — used by tests and by
    anyone building a webhook-sending simulator against the "generic"
    scheme; a real provider's own signing happens on their side, not here."""
    return hmac.new(_webhook_secret().encode(), body, hashlib.sha256).hexdigest()


def _verify_generic_hmac(body: bytes, headers: dict[str, str]) -> bool:
    signature = headers.get("x-webhook-signature")
    if not signature:
        return False
    expected = hmac.new(_webhook_secret().encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(provider: str, body: bytes, headers: dict[str, str]) -> bool:
    """`headers` keys must already be lower-cased by the caller (FastAPI's
    `Request.headers` is case-insensitive but iterating it isn't — routes
    pass `dict(request.headers)` which lower-cases automatically)."""
    if provider == "generic":
        return _verify_generic_hmac(body, headers)
    return False
