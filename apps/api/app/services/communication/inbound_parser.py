"""
Inbound-email payload parsing, keyed by provider name — mirrors
`app.services.email.sender_client`'s single-dispatch-point shape exactly:
one `parse_inbound_payload(provider, payload)` function, no branching
outside it, so `InboundEmailService` never has to know which provider sent
a given webhook.

Two concrete shapes are implemented: "generic" (this system's own clean
JSON shape — what a custom forwarding function or a not-yet-integrated ESP
would send) and "postmark" (Postmark's real Inbound Webhook JSON shape,
documented and simple enough to implement exactly rather than
approximately). A real SendGrid Inbound Parse / Mailgun Routes integration
adds its own parser function here, dispatched the same way.
"""

from dataclasses import dataclass

from app.exceptions.errors import ValidationError


@dataclass
class ParsedInboundEmail:
    from_email: str
    from_name: str | None
    to_email: str
    subject: str | None
    body_text: str
    body_html: str | None
    external_message_id: str | None
    in_reply_to: str | None


def _parse_generic(payload: dict) -> ParsedInboundEmail:
    from_email = payload.get("from_email")
    to_email = payload.get("to_email")
    body_text = payload.get("body_text")
    if not from_email or not to_email or not body_text:
        raise ValidationError("Inbound payload missing from_email, to_email, or body_text.")
    return ParsedInboundEmail(
        from_email=from_email, from_name=payload.get("from_name"), to_email=to_email,
        subject=payload.get("subject"), body_text=body_text, body_html=payload.get("body_html"),
        external_message_id=payload.get("message_id"), in_reply_to=payload.get("in_reply_to"),
    )


def _parse_postmark(payload: dict) -> ParsedInboundEmail:
    from_full = payload.get("FromFull") or {}
    to_full = payload.get("ToFull") or []
    body_text = payload.get("TextBody")
    from_email = from_full.get("Email")
    to_email = to_full[0].get("Email") if to_full else None
    if not from_email or not to_email or not body_text:
        raise ValidationError("Postmark inbound payload missing FromFull.Email, ToFull[0].Email, or TextBody.")

    in_reply_to = None
    for header in payload.get("Headers") or []:
        if header.get("Name", "").lower() == "in-reply-to":
            in_reply_to = header.get("Value")
            break

    return ParsedInboundEmail(
        from_email=from_email, from_name=from_full.get("Name"), to_email=to_email,
        subject=payload.get("Subject"), body_text=body_text, body_html=payload.get("HtmlBody"),
        external_message_id=payload.get("MessageID"), in_reply_to=in_reply_to,
    )


_PARSERS = {
    "generic": _parse_generic,
    "postmark": _parse_postmark,
}


def parse_inbound_payload(provider: str, payload: dict) -> ParsedInboundEmail:
    parser = _PARSERS.get(provider)
    if parser is None:
        raise ValidationError(f"Unsupported inbound email provider: '{provider}'.")
    return parser(payload)
