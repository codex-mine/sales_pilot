import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Role
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio


async def _get_role_id(db: AsyncSession, organization_id: str, name: str) -> str:
    role = await db.scalar(
        select(Role).where(Role.organization_id == organization_id, Role.name == name)
    )
    assert role is not None, f"role '{name}' was not seeded for this organization"
    return str(role.id)


async def _invite_and_accept(
    client: AsyncClient, db: AsyncSession, *, owner_organization_id: str, role_name: str
) -> AsyncClient:
    """Invites + accepts as a fresh member, returning a *new* logged-in AsyncClient
    (same app, independent cookie jar) so the owner's session is untouched."""
    role_id = await _get_role_id(db, owner_organization_id, role_name)
    invite_email = unique_email(role_name)
    invite_response = await client.post(
        "/api/v1/organizations/invitations",
        json={"email": invite_email, "role_id": role_id},
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_token = invite_response.json()["meta"]["debug_invitation_token"]

    member_client = AsyncClient(transport=client._transport, base_url="http://test")
    accept_response = await member_client.post(
        "/api/v1/organizations/invitations/accept",
        json={
            "token": invite_token,
            "first_name": "New",
            "last_name": role_name.title(),
            "password": "Str0ng!Passw0rd",
        },
    )
    assert accept_response.status_code == 201, accept_response.text
    return member_client


async def test_owner_has_every_permission(client: AsyncClient) -> None:
    body = await register_user(client)
    permissions = (await client.get("/api/v1/auth/me")).json()["data"]["permissions"]
    assert "billing.manage" in permissions
    assert "organizations.manage" in permissions
    assert body["data"] is not None or body["success"]  # sanity: registration succeeded


async def test_member_lacks_user_management_permission(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]

    member_client = await _invite_and_accept(
        client, db, owner_organization_id=org_id, role_name="member"
    )
    try:
        response = await member_client.post(
            "/api/v1/organizations/invitations",
            json={"email": unique_email(), "role_id": await _get_role_id(db, org_id, "viewer")},
        )
        assert response.status_code == 403
        assert response.json()["errors"]["error_code"] == ["permission_denied"]
    finally:
        await member_client.aclose()


async def test_viewer_cannot_read_users_but_owner_can_invite(
    client: AsyncClient, db: AsyncSession
) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]

    viewer_client = await _invite_and_accept(
        client, db, owner_organization_id=org_id, role_name="viewer"
    )
    try:
        response = await viewer_client.get("/api/v1/organizations/invitations")
        assert response.status_code == 403
    finally:
        await viewer_client.aclose()

    # Owner still can, proving the 403 above was role-specific, not a bug in the route.
    owner_list_response = await client.get("/api/v1/organizations/invitations")
    assert owner_list_response.status_code == 200


async def test_accepting_invitation_for_existing_email_is_rejected(
    client: AsyncClient, db: AsyncSession
) -> None:
    existing_email = unique_email("existing")
    await register_user(client, email=existing_email)
    owner_body = (await client.get("/api/v1/auth/me")).json()["data"]
    org_id = owner_body["organization"]["id"]
    role_id = await _get_role_id(db, org_id, "viewer")

    invite_response = await client.post(
        "/api/v1/organizations/invitations",
        json={"email": existing_email, "role_id": role_id},
    )
    # A pending invite can't even be created for an email that's already a user.
    assert invite_response.status_code == 409
