import base64
import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Organization, Role
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio

# A real, valid 1x1 transparent PNG (well-known test fixture bytes).
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def _get_role_id(db: AsyncSession, organization_id: str, name: str) -> str:
    role = await db.scalar(
        select(Role).where(Role.organization_id == organization_id, Role.name == name)
    )
    assert role is not None, f"role '{name}' was not seeded for this organization"
    return str(role.id)


async def _invite_and_accept(
    client: AsyncClient, db: AsyncSession, *, owner_organization_id: str, role_name: str
) -> AsyncClient:
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


# ─── Read ───────────────────────────────────────────────────────────────────────

async def test_get_current_organization(client: AsyncClient) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]

    response = await client.get("/api/v1/organizations/current")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == org_id
    assert data["member_count"] == 1
    assert data["language"] == "en"
    assert data["currency"] == "USD"


async def test_list_organizations_returns_only_own_org(client: AsyncClient) -> None:
    body = await register_user(client)
    response = await client.get("/api/v1/organizations")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == body["data"]["organization_id"]


async def test_get_organization_by_id_matches_current(client: AsyncClient) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]
    response = await client.get(f"/api/v1/organizations/{org_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == org_id


async def test_get_organization_by_foreign_id_is_not_found(client: AsyncClient) -> None:
    await register_user(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/organizations/{fake_id}")
    assert response.status_code == 404


async def test_create_organization_is_not_supported(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post("/api/v1/organizations", json={"name": "Second Org"})
    assert response.status_code == 409


# ─── Update ─────────────────────────────────────────────────────────────────────

async def test_update_current_organization_profile_fields(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.patch(
        "/api/v1/organizations/current",
        json={
            "name": "Renamed Inc",
            "website": "https://example.com",
            "email": "hello@example.com",
            "phone": "+1 555 0100",
            "industry": "Software",
            "country": "United States",
            "company_size": "11-50",
            "description": "We sell things.",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["name"] == "Renamed Inc"
    assert data["website"] == "https://example.com"
    assert data["email"] == "hello@example.com"
    assert data["company_size"] == "11-50"


async def test_update_settings_fields(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.patch(
        "/api/v1/organizations/current",
        json={
            "timezone": "America/New_York",
            "language": "en-US",
            "currency": "EUR",
            "brand_color": "#16A34A",
            "address": {"line1": "1 Infinite Loop", "city": "Cupertino", "postal_code": "95014"},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["timezone"] == "America/New_York"
    assert data["currency"] == "EUR"
    assert data["brand_color"] == "#16A34A"
    assert data["address"]["city"] == "Cupertino"


async def test_update_rejects_invalid_timezone(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.patch(
        "/api/v1/organizations/current", json={"timezone": "Not/A_Real_Zone"}
    )
    assert response.status_code == 422


async def test_update_rejects_invalid_brand_color(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.patch(
        "/api/v1/organizations/current", json={"brand_color": "not-a-color"}
    )
    assert response.status_code == 422


async def test_update_accepts_explicit_null_for_optional_validated_fields(client: AsyncClient) -> None:
    """
    Regression test: a PATCH payload that explicitly clears an optional field
    (e.g. a form re-submitting `company_size: null` for "no selection") must
    not be rejected just because that field also has a format validator —
    the validator should only run against a real value, not against the
    "field wasn't set" case.
    """
    await register_user(client)
    response = await client.patch(
        "/api/v1/organizations/current",
        json={"company_size": None, "brand_color": None},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["company_size"] is None
    assert data["brand_color"] is None


async def test_update_slug_conflict(client: AsyncClient, db: AsyncSession) -> None:
    await register_user(client, email=unique_email("first"))
    first_org = (await client.get("/api/v1/auth/me")).json()["data"]["organization"]["slug"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client, email=unique_email("second"))
    response = await other_client.patch("/api/v1/organizations/current", json={"slug": first_org})
    assert response.status_code == 409
    await other_client.aclose()


async def test_member_cannot_update_organization(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    member_client = await _invite_and_accept(
        client, db, owner_organization_id=org_id, role_name="member"
    )
    try:
        # A member CAN read the org (organizations.read is granted to every role)...
        assert (await member_client.get("/api/v1/organizations/current")).status_code == 200
        # ...but cannot update or delete it.
        assert (
            await member_client.patch("/api/v1/organizations/current", json={"name": "Hijacked"})
        ).status_code == 403
        org_id_url = f"/api/v1/organizations/{org_id}"
        assert (await member_client.delete(org_id_url)).status_code == 403
    finally:
        await member_client.aclose()


# ─── Delete ─────────────────────────────────────────────────────────────────────

async def test_owner_can_delete_organization(client: AsyncClient, db: AsyncSession) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]

    response = await client.delete(f"/api/v1/organizations/{org_id}")
    assert response.status_code == 200

    organization = await db.get(Organization, org_id)
    assert organization is not None
    assert organization.is_active is False
    assert organization.deleted_at is not None

    # The owner's own session is now locked out of everything org-scoped.
    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code in (401, 403, 404)


async def test_admin_cannot_delete_organization(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    admin_client = await _invite_and_accept(
        client, db, owner_organization_id=org_id, role_name="admin"
    )
    try:
        response = await admin_client.delete(f"/api/v1/organizations/{org_id}")
        assert response.status_code == 403
    finally:
        await admin_client.aclose()


# ─── Logo ───────────────────────────────────────────────────────────────────────

async def test_upload_and_delete_logo(client: AsyncClient) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]

    upload_response = await client.post(
        f"/api/v1/organizations/{org_id}/logo",
        files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    assert upload_response.status_code == 200, upload_response.text
    logo_url = upload_response.json()["data"]["logo_url"]
    assert logo_url is not None
    assert logo_url.startswith(f"/media/organizations/{org_id}/logo.png")

    delete_response = await client.delete(f"/api/v1/organizations/{org_id}/logo")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["logo_url"] is None


async def test_upload_logo_rejects_non_image(client: AsyncClient) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]

    response = await client.post(
        f"/api/v1/organizations/{org_id}/logo",
        files={"file": ("not-an-image.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 400


# ─── Members ────────────────────────────────────────────────────────────────────

async def test_list_members_includes_owner(client: AsyncClient) -> None:
    body = await register_user(client)
    org_id = body["data"]["organization_id"]

    response = await client.get(f"/api/v1/organizations/{org_id}/members")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["role"] == "owner"
    assert payload["data"][0]["email"] == body["data"]["email"]


async def test_list_members_search_and_pagination(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    for role_name in ("admin", "member", "viewer"):
        colleague = await _invite_and_accept(
            client, db, owner_organization_id=org_id, role_name=role_name
        )
        await colleague.aclose()

    all_members = await client.get(f"/api/v1/organizations/{org_id}/members")
    assert all_members.json()["meta"]["total"] == 4

    paged = await client.get(f"/api/v1/organizations/{org_id}/members?page=1&page_size=2")
    assert len(paged.json()["data"]) == 2
    assert paged.json()["meta"]["total"] == 4

    filtered = await client.get(f"/api/v1/organizations/{org_id}/members?role=admin")
    assert filtered.json()["meta"]["total"] == 1
    assert filtered.json()["data"][0]["role"] == "admin"


async def test_viewer_cannot_list_members(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    viewer_client = await _invite_and_accept(
        client, db, owner_organization_id=org_id, role_name="viewer"
    )
    try:
        response = await viewer_client.get(f"/api/v1/organizations/{org_id}/members")
        assert response.status_code == 403
    finally:
        await viewer_client.aclose()
