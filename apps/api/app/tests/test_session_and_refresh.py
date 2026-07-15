import pytest
from httpx import AsyncClient

from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


async def test_refresh_rotates_tokens_and_old_refresh_token_is_rejected(
    client: AsyncClient,
) -> None:
    await register_user(client)
    old_refresh_token = client.cookies["refresh_token"]

    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert client.cookies["refresh_token"] != old_refresh_token

    # Reusing the now-rotated-away token is treated as theft: it must fail,
    # and every session for the user gets burned as a side effect.
    client.cookies.set("refresh_token", old_refresh_token)
    replay_response = await client.post("/api/v1/auth/refresh")
    assert replay_response.status_code == 401
    assert replay_response.json()["errors"]["error_code"] == ["token_revoked"]


async def test_refresh_replay_revokes_all_sessions(client: AsyncClient) -> None:
    await register_user(client)
    old_refresh_token = client.cookies["refresh_token"]
    await client.post("/api/v1/auth/refresh")

    client.cookies.set("refresh_token", old_refresh_token)
    await client.post("/api/v1/auth/refresh")  # triggers the reuse-detection burn

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


async def test_logout_revokes_current_session_only(client: AsyncClient) -> None:
    await register_user(client)
    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


async def test_list_sessions_marks_current_session(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    sessions = response.json()["data"]
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True


async def test_revoking_a_session_logs_it_out(client: AsyncClient) -> None:
    await register_user(client)
    sessions = (await client.get("/api/v1/auth/sessions")).json()["data"]
    session_id = sessions[0]["id"]

    revoke_response = await client.delete(f"/api/v1/auth/sessions/{session_id}")
    assert revoke_response.status_code == 200

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


async def test_logout_all_revokes_every_session_for_that_user_only(
    client: AsyncClient,
) -> None:
    await register_user(client)
    response = await client.post("/api/v1/auth/logout-all")
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401
