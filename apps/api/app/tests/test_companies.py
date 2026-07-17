import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio


async def _create_company(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": "Acme Corp",
        "website": "https://www.acme.example.com",
        "industry": "SaaS",
        "status": "prospect",
        **overrides,
    }
    response = await client.post("/api/v1/companies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _invite_and_accept(
    client: AsyncClient, db: AsyncSession, *, owner_organization_id: str, role_name: str
) -> AsyncClient:
    from sqlalchemy import select

    from app.models.identity.models import Role

    role = await db.scalar(
        select(Role).where(Role.organization_id == owner_organization_id, Role.name == role_name)
    )
    assert role is not None
    invite_email = unique_email(role_name)
    invite_response = await client.post(
        "/api/v1/organizations/invitations", json={"email": invite_email, "role_id": str(role.id)}
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_token = invite_response.json()["meta"]["debug_invitation_token"]

    member_client = AsyncClient(transport=client._transport, base_url="http://test")
    accept_response = await member_client.post(
        "/api/v1/organizations/invitations/accept",
        json={
            "token": invite_token, "first_name": "New", "last_name": role_name.title(),
            "password": "Str0ng!Passw0rd",
        },
    )
    assert accept_response.status_code == 201, accept_response.text
    return member_client


# ─── CRUD ───────────────────────────────────────────────────────────────────────

async def test_create_and_get_company(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)
    response = await client.get(f"/api/v1/companies/{company['id']}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Acme Corp"
    assert data["domain"] == "acme.example.com"
    assert data["notes_count"] == 0
    assert data["is_archived"] is False


async def test_create_company_rejects_duplicate_domain(client: AsyncClient) -> None:
    await register_user(client)
    await _create_company(client, website="https://dupe.example.com")
    response = await client.post(
        "/api/v1/companies", json={"name": "Other Co", "website": "https://www.dupe.example.com"}
    )
    assert response.status_code == 400


async def test_update_company_tracks_status_change(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)
    response = await client.patch(f"/api/v1/companies/{company['id']}", json={"status": "active"})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "active"

    activities = await client.get(f"/api/v1/companies/{company['id']}/activities")
    types = [a["activity_type"] for a in activities.json()["data"]]
    assert "status_changed" in types
    assert "company_created" in types


async def test_archive_and_restore_company(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)

    archive = await client.post(f"/api/v1/companies/{company['id']}/archive")
    assert archive.json()["data"]["is_archived"] is True

    listing = await client.get("/api/v1/companies")
    assert company["id"] not in [item["id"] for item in listing.json()["data"]]

    explicit = await client.get("/api/v1/companies?archived=true")
    assert company["id"] in [item["id"] for item in explicit.json()["data"]]

    restore = await client.post(f"/api/v1/companies/{company['id']}/restore")
    assert restore.json()["data"]["is_archived"] is False


async def test_delete_company_soft_deletes(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)
    response = await client.delete(f"/api/v1/companies/{company['id']}")
    assert response.status_code == 200
    assert (await client.get(f"/api/v1/companies/{company['id']}")).status_code == 404


async def test_create_company_with_tags(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client, tags=["Hot", "Enterprise"], website="https://tagco.example.com")
    assert {t["name"] for t in company["tags"]} == {"Hot", "Enterprise"}

    tags_response = await client.get("/api/v1/companies/tags")
    assert {t["name"] for t in tags_response.json()["data"]} >= {"Hot", "Enterprise"}


async def test_assign_owner_validates_same_organization(client: AsyncClient) -> None:
    body = await register_user(client)
    company = await _create_company(client)
    fake_owner_id = "00000000-0000-0000-0000-000000000000"
    response = await client.patch(f"/api/v1/companies/{company['id']}", json={"owner_id": fake_owner_id})
    assert response.status_code == 400

    own_id = body["data"]["id"]
    valid = await client.patch(f"/api/v1/companies/{company['id']}", json={"owner_id": own_id})
    assert valid.status_code == 200
    assert valid.json()["data"]["owner"]["id"] == own_id


# ─── Search / filter / sort / pagination ───────────────────────────────────────

async def test_search_by_name(client: AsyncClient) -> None:
    await register_user(client)
    await _create_company(client, name="Quantum Widgets", website="https://quantum.example.com")
    await _create_company(client, name="Beta Corp", website="https://beta.example.com")

    response = await client.get("/api/v1/companies?search=quantum")
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Quantum Widgets"


async def test_filter_by_status_and_pagination(client: AsyncClient) -> None:
    await register_user(client)
    for i in range(5):
        await _create_company(client, name=f"Company{i}", website=f"https://page{i}.example.com")
    await _create_company(client, name="Active Co", status="active", website="https://activeco.example.com")

    filtered = await client.get("/api/v1/companies?status=active")
    assert filtered.json()["meta"]["total"] == 1

    paged = await client.get("/api/v1/companies?page=1&page_size=3")
    assert len(paged.json()["data"]) == 3
    assert paged.json()["meta"]["total"] == 6


async def test_sort_by_name(client: AsyncClient) -> None:
    await register_user(client)
    await _create_company(client, name="Zeta Inc", website="https://zeta.example.com")
    await _create_company(client, name="Alpha Inc", website="https://alpha.example.com")

    response = await client.get("/api/v1/companies?sort_by=name&sort_desc=false")
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Alpha Inc") < names.index("Zeta Inc")


# ─── Notes (shared NoteService — same table as Lead notes) ─────────────────────

async def test_note_crud(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)

    create = await client.post(
        f"/api/v1/companies/{company['id']}/notes", json={"content": "Called them.", "is_pinned": False}
    )
    assert create.status_code == 201
    note = create.json()["data"]
    assert note["author_name"] is not None

    update = await client.patch(
        f"/api/v1/companies/{company['id']}/notes/{note['id']}",
        json={"content": "Called them, left voicemail.", "is_pinned": True},
    )
    assert update.status_code == 200
    assert update.json()["data"]["is_pinned"] is True

    listing = await client.get(f"/api/v1/companies/{company['id']}/notes")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    delete = await client.delete(f"/api/v1/companies/{company['id']}/notes/{note['id']}")
    assert delete.status_code == 200

    company_after = await client.get(f"/api/v1/companies/{company['id']}")
    assert company_after.json()["data"]["notes_count"] == 0


# ─── Attachments (shared AttachmentService — same table as Lead attachments) ────

async def test_attachment_upload_and_delete(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)

    upload = await client.post(
        f"/api/v1/companies/{company['id']}/attachments",
        files={"file": ("proposal.pdf", io.BytesIO(b"%PDF-1.4 fake pdf content"), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    attachment = upload.json()["data"]
    assert attachment["filename"] == "proposal.pdf"
    assert attachment["file_url"].startswith("/media/organizations/")

    listing = await client.get(f"/api/v1/companies/{company['id']}/attachments")
    assert len(listing.json()["data"]) == 1

    delete = await client.delete(f"/api/v1/companies/{company['id']}/attachments/{attachment['id']}")
    assert delete.status_code == 200


async def test_attachment_rejects_unsupported_type(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)
    response = await client.post(
        f"/api/v1/companies/{company['id']}/attachments",
        files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert response.status_code == 400


# ─── Employees (read-only Contact view) ─────────────────────────────────────────

async def test_employees_lists_linked_contacts(client: AsyncClient, db: AsyncSession) -> None:
    await register_user(client)
    company = await _create_company(client)

    from app.models.crm.models import Contact

    contact = Contact(
        organization_id=company["organization_id"],
        company_id=company["id"],
        first_name="Grace", last_name="Hopper", email=unique_email("grace"),
        job_title="Rear Admiral",
    )
    db.add(contact)
    await db.commit()

    response = await client.get(f"/api/v1/companies/{company['id']}/employees")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["full_name"] == "Grace Hopper"
    assert data[0]["has_linked_lead"] is False

    search = await client.get(f"/api/v1/companies/{company['id']}/employees?search=grace")
    assert len(search.json()["data"]) == 1

    miss = await client.get(f"/api/v1/companies/{company['id']}/employees?search=nobody")
    assert len(miss.json()["data"]) == 0


# ─── Bulk actions ───────────────────────────────────────────────────────────────

async def test_bulk_archive_and_restore(client: AsyncClient) -> None:
    await register_user(client)
    company1 = await _create_company(client, website="https://bulk1.example.com")
    company2 = await _create_company(client, website="https://bulk2.example.com")

    archive = await client.post(
        "/api/v1/companies/bulk", json={"company_ids": [company1["id"], company2["id"]], "action": "archive"}
    )
    assert archive.status_code == 200
    assert archive.json()["data"]["success_count"] == 2

    restore = await client.post(
        "/api/v1/companies/bulk", json={"company_ids": [company1["id"]], "action": "restore"}
    )
    assert restore.json()["data"]["success_count"] == 1


async def test_bulk_add_and_remove_tags(client: AsyncClient) -> None:
    await register_user(client)
    company1 = await _create_company(client, website="https://t1.example.com")
    company2 = await _create_company(client, website="https://t2.example.com")

    add = await client.post(
        "/api/v1/companies/bulk",
        json={"company_ids": [company1["id"], company2["id"]], "action": "add_tags", "tags": ["Priority"]},
    )
    assert add.json()["data"]["success_count"] == 2

    company1_after = await client.get(f"/api/v1/companies/{company1['id']}")
    assert "Priority" in [t["name"] for t in company1_after.json()["data"]["tags"]]


async def test_bulk_partial_failure_reports_errors(client: AsyncClient) -> None:
    await register_user(client)
    company = await _create_company(client)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        "/api/v1/companies/bulk", json={"company_ids": [company["id"], fake_id], "action": "archive"}
    )
    body = response.json()["data"]
    assert body["success_count"] == 1
    assert body["failed_count"] == 1


# ─── CSV export ─────────────────────────────────────────────────────────────────

async def test_export_csv(client: AsyncClient) -> None:
    await register_user(client)
    await _create_company(client, name="Export Me", website="https://exportme.example.com")

    response = await client.get("/api/v1/companies/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Export Me" in response.text
    assert "attachment" in response.headers["content-disposition"]


async def test_export_selected_companies_only(client: AsyncClient) -> None:
    await register_user(client)
    company1 = await _create_company(client, name="Keep Co", website="https://keep.example.com")
    await _create_company(client, name="Skip Co", website="https://skip.example.com")

    response = await client.get(f"/api/v1/companies/export?company_ids={company1['id']}")
    assert "Keep Co" in response.text
    assert "Skip Co" not in response.text


# ─── Permissions ────────────────────────────────────────────────────────────────

async def test_sales_role_cannot_delete_export_bulk(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    sales_client = await _invite_and_accept(client, db, owner_organization_id=org_id, role_name="sales")
    try:
        company_response = await sales_client.post(
            "/api/v1/companies", json={"name": "Sales Owned", "website": "https://salesowned.example.com"}
        )
        assert company_response.status_code == 201
        company_id = company_response.json()["data"]["id"]

        assert (await sales_client.delete(f"/api/v1/companies/{company_id}")).status_code == 403
        assert (await sales_client.get("/api/v1/companies/export")).status_code == 403
        assert (
            await sales_client.post(
                "/api/v1/companies/bulk", json={"company_ids": [company_id], "action": "archive"}
            )
        ).status_code == 403

        # But sales CAN add a note (notes.manage is granted).
        note_response = await sales_client.post(
            f"/api/v1/companies/{company_id}/notes", json={"content": "Following up."}
        )
        assert note_response.status_code == 201
    finally:
        await sales_client.aclose()


async def test_viewer_cannot_create_companies(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    viewer_client = await _invite_and_accept(client, db, owner_organization_id=org_id, role_name="viewer")
    try:
        response = await viewer_client.post(
            "/api/v1/companies", json={"name": "Nope Co", "website": "https://nopeco.example.com"}
        )
        assert response.status_code == 403
    finally:
        await viewer_client.aclose()
