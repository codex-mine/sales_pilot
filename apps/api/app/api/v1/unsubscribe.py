"""
Public, unauthenticated unsubscribe routes (CAN-SPAM one-click unsubscribe).

No route in this file depends on `require_permission` or any auth
dependency — this is the ENTIRE, narrowest-possible exclusion from the
authenticated route surface (see `app/auth/dependencies.py`: routes are
public by simply not depending on `require_permission`/`get_current_user`;
there is no global auth-enforcing middleware to separately exclude these
from). Kept in its own file, rather than folded into `emails.py`, so that
"this file has zero auth dependencies" is trivially auditable.

Token validation never leaks whether a lead/email exists: any decode
failure (bad signature, wrong type, or a `sub` that no longer resolves to a
lead) returns the exact same generic error.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.exceptions.errors import AuthenticationError, NotFoundError
from app.schemas.common import ApiResponse
from app.schemas.email_sending import UnsubscribeConfirmResponse, UnsubscribeInfoResponse
from app.security.tokens import decode_token
from app.services.email.email_sending_service import EmailSendingService

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


def _decode(token: str) -> tuple[uuid.UUID, uuid.UUID]:
    try:
        payload = decode_token(token, expected_type="unsubscribe")
        return uuid.UUID(payload["sub"]), uuid.UUID(payload["organization_id"])
    except (AuthenticationError, KeyError, ValueError) as exc:
        raise NotFoundError("This link is invalid or has expired.") from exc


@router.get("/{token}", response_model=ApiResponse[UnsubscribeInfoResponse])
async def get_unsubscribe_info(token: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[UnsubscribeInfoResponse]:
    lead_id, organization_id = _decode(token)
    info = await EmailSendingService(db).get_unsubscribe_info(lead_id, organization_id)
    return ApiResponse(data=UnsubscribeInfoResponse(**info))


@router.post("/{token}", response_model=ApiResponse[UnsubscribeConfirmResponse])
async def confirm_unsubscribe(token: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[UnsubscribeConfirmResponse]:
    lead_id, organization_id = _decode(token)
    info = await EmailSendingService(db).process_unsubscribe(lead_id, organization_id)
    return ApiResponse(data=UnsubscribeConfirmResponse(**info), message="You have been unsubscribed.")
