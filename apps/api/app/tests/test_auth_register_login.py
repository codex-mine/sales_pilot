import pytest
from httpx import AsyncClient

from app.tests.conftest import REGISTER_PAYLOAD, register_user, unique_email

pytestmark = pytest.mark.asyncio


async def test_register_creates_owner_with_full_permissions(client: AsyncClient) -> None:
    body = await register_user(client)
    assert body["success"] is True
    assert body["data"]["role"] == "owner"
    assert body["data"]["status"] == "pending_verification"
    assert body["data"]["email_verified"] is False
    # Registration also logs the caller in.
    assert "access_token" in client.cookies
    assert "refresh_token" in client.cookies


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    email = unique_email()
    await register_user(client, email=email)
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": email},
    )
    assert response.status_code == 409
    assert response.json()["success"] is False


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": unique_email(), "password": "weak"},
    )
    assert response.status_code == 422


async def test_login_with_correct_credentials(client: AsyncClient) -> None:
    email = unique_email()
    await register_user(client, email=email)
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == email


async def test_login_with_wrong_password_fails(client: AsyncClient) -> None:
    email = unique_email()
    await register_user(client, email=email)
    client.cookies.clear()
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "WrongPassw0rd!"}
    )
    assert response.status_code == 401
    assert response.json()["errors"]["error_code"] == ["invalid_credentials"]


async def test_login_with_unknown_email_fails_like_wrong_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email(), "password": "Whatever!Pass1"},
    )
    assert response.status_code == 401
    assert response.json()["errors"]["error_code"] == ["invalid_credentials"]


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_organization_and_permissions(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["organization"]["name"] == "Acme Inc"
    assert body["workspace"]["id"] == body["organization"]["id"]
    assert "leads.read" in body["permissions"]
    assert "billing.manage" in body["permissions"]
