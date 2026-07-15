from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import get_settings
from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


def _encode(payload: dict) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def test_missing_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["errors"]["error_code"] == ["authentication_error"]


async def test_tampered_signature_is_rejected(client: AsyncClient) -> None:
    await register_user(client)
    tampered = client.cookies["access_token"][:-4] + "abcd"
    client.cookies.set("access_token", tampered)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_garbage_token_is_rejected(client: AsyncClient) -> None:
    client.cookies.set("access_token", "not-a-jwt-at-all")
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_expired_access_token_is_rejected(client: AsyncClient) -> None:
    await register_user(client)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "organization_id": "00000000-0000-0000-0000-000000000000",
        "workspace_id": "00000000-0000-0000-0000-000000000000",
        "role_id": None,
        "role_name": None,
        "permissions_version": 1,
        "session_id": "00000000-0000-0000-0000-000000000000",
        "type": "access",
        "iss": settings.jwt_issuer,
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
        "jti": "expired-test-jti",
    }
    client.cookies.set("access_token", _encode(expired_payload))
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_token_rejected_as_access_token(client: AsyncClient) -> None:
    """A refresh token has `type: refresh` — using it where an access token is
    expected must fail the type check, not just signature verification."""
    await register_user(client)
    refresh_token = client.cookies["refresh_token"]
    client.cookies.set("access_token", refresh_token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_access_token_rejected_as_refresh_token(client: AsyncClient) -> None:
    await register_user(client)
    access_token = client.cookies["access_token"]
    client.cookies.set("refresh_token", access_token)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


async def test_token_for_deleted_session_is_rejected(client: AsyncClient) -> None:
    await register_user(client)
    access_token = client.cookies["access_token"]
    await client.post("/api/v1/auth/logout")  # revokes the session server-side + clears cookies

    # Replay the pre-logout access token explicitly: it's still a
    # cryptographically valid, unexpired JWT — only the server-side session
    # revocation should be what blocks it now.
    client.cookies.set("access_token", access_token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["errors"]["error_code"] == ["session_expired"]
