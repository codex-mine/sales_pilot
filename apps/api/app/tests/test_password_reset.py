import pytest
from httpx import AsyncClient

from app.tests.conftest import REGISTER_PAYLOAD, register_user, unique_email

pytestmark = pytest.mark.asyncio


async def test_forgot_password_does_not_reveal_whether_email_exists(client: AsyncClient) -> None:
    known_email = unique_email()
    await register_user(client, email=known_email)

    known_response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": known_email}
    )
    unknown_response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": unique_email()}
    )
    assert known_response.status_code == unknown_response.status_code == 200
    assert known_response.json()["message"] == unknown_response.json()["message"]
    # Only the real account gets a debug token back.
    assert known_response.json()["meta"]["debug_reset_token"]
    assert unknown_response.json()["meta"] is None


async def test_reset_password_changes_password_and_revokes_sessions(
    client: AsyncClient,
) -> None:
    email = unique_email()
    await register_user(client, email=email)

    forgot_response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    reset_token = forgot_response.json()["meta"]["debug_reset_token"]

    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewStr0ng!Pass99"},
    )
    assert reset_response.status_code == 200

    # The session that was active at reset time is dead now.
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    client.cookies.clear()
    old_password_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": REGISTER_PAYLOAD["password"]},
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "NewStr0ng!Pass99"}
    )
    assert new_password_login.status_code == 200


async def test_reset_token_is_single_use(client: AsyncClient) -> None:
    email = unique_email()
    await register_user(client, email=email)
    reset_token = (
        await client.post("/api/v1/auth/forgot-password", json={"email": email})
    ).json()["meta"]["debug_reset_token"]

    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "FirstNew!Pass99"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "SecondNew!Pass99"},
    )
    assert second.status_code == 401


async def test_change_password_requires_correct_current_password(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongCurrent!1", "new_password": "Another!Pass99"},
    )
    assert response.status_code == 401


async def test_change_password_succeeds_with_correct_current_password(
    client: AsyncClient,
) -> None:
    email = unique_email()
    await register_user(client, email=email)
    response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": REGISTER_PAYLOAD["password"],
            "new_password": "Freshly!Changed99",
        },
    )
    assert response.status_code == 200

    client.cookies.clear()
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Freshly!Changed99"}
    )
    assert login_response.status_code == 200
