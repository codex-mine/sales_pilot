"""
Public, unauthenticated open-pixel and click-redirect routes (Email
Tracking). No route in this file depends on `require_permission` or any
auth dependency — same "public by simply not depending on auth" mechanism
`unsubscribe.py` (module 07) already established; kept in its own file for
the same auditability reason.

The pixel endpoint must never error or delay on a lookup miss — an email
client waiting on this response is exactly what module 08's spec warns
against ("do not make the recipient's mail client wait"). The click
endpoint must never become an open redirector for unsigned/tampered input.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.services.email.email_tracking_service import TRACKING_PIXEL_PNG, EmailTrackingService

router = APIRouter(prefix="/track", tags=["track"])

_PNG_HEADERS = {
    "Content-Type": "image/png",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


@router.get("/open/{tracking_pixel_id}.png")
async def track_open(
    tracking_pixel_id: str, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    try:
        await EmailTrackingService(db).record_open(
            tracking_pixel_id, ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:  # noqa: BLE001 — the pixel response must never fail, whatever went wrong recording it
        pass
    return Response(content=TRACKING_PIXEL_PNG, headers=_PNG_HEADERS)


@router.get("/click/{tracking_pixel_id}")
async def track_click(
    tracking_pixel_id: str, url: str, sig: str, request: Request, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    try:
        target = await EmailTrackingService(db).resolve_click(
            tracking_pixel_id, url, sig,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:  # noqa: BLE001 — never surface an error to the recipient's browser
        target = get_settings().frontend_url
    return RedirectResponse(url=target, status_code=302)
