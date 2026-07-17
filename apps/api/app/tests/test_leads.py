import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio


async def _create_lead(client: AsyncClient, **overrides) -> dict:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": unique_email("lead"),
        "company_name": "Analytical Engines Inc",
        "status": "new",
        "priority": 50,
        **overrides,
    }
    response = await client.post("/api/v1/leads", json=payload)
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

async def test_create_lead_requires_some_identity(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post("/api/v1/leads", json={"priority": 10})
    assert response.status_code == 400


async def test_create_and_get_lead(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    response = await client.get(f"/api/v1/leads/{lead['id']}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] == "Ada Lovelace"
    assert data["notes_count"] == 0
    assert data["is_archived"] is False


async def test_update_lead_tracks_status_change(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    response = await client.patch(f"/api/v1/leads/{lead['id']}", json={"status": "contacted"})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "contacted"

    activities = await client.get(f"/api/v1/leads/{lead['id']}/activities")
    types = [a["activity_type"] for a in activities.json()["data"]]
    assert "status_changed" in types
    assert "lead_created" in types


async def test_favorite_and_archive_via_update(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    fav = await client.patch(f"/api/v1/leads/{lead['id']}", json={"is_favorite": True})
    assert fav.json()["data"]["is_favorite"] is True

    archive = await client.patch(f"/api/v1/leads/{lead['id']}", json={"is_archived": True})
    assert archive.json()["data"]["is_archived"] is True

    # Archived leads are hidden from the default list view.
    listing = await client.get("/api/v1/leads")
    assert lead["id"] not in [item["id"] for item in listing.json()["data"]]

    explicit = await client.get("/api/v1/leads?archived=true")
    assert lead["id"] in [item["id"] for item in explicit.json()["data"]]


async def test_delete_lead_soft_deletes(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    response = await client.delete(f"/api/v1/leads/{lead['id']}")
    assert response.status_code == 200
    assert (await client.get(f"/api/v1/leads/{lead['id']}")).status_code == 404


async def test_create_lead_with_tags(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client, tags=["Hot", "Enterprise"])
    assert {t["name"] for t in lead["tags"]} == {"Hot", "Enterprise"}

    tags_response = await client.get("/api/v1/leads/tags")
    assert {t["name"] for t in tags_response.json()["data"]} >= {"Hot", "Enterprise"}


async def test_assign_owner_validates_same_organization(client: AsyncClient) -> None:
    body = await register_user(client)
    lead = await _create_lead(client)
    fake_owner_id = "00000000-0000-0000-0000-000000000000"
    response = await client.patch(f"/api/v1/leads/{lead['id']}", json={"owner_id": fake_owner_id})
    assert response.status_code == 400

    own_id = body["data"]["id"]
    valid = await client.patch(f"/api/v1/leads/{lead['id']}", json={"owner_id": own_id})
    assert valid.status_code == 200
    assert valid.json()["data"]["owner"]["id"] == own_id


# ─── Search / filter / sort / pagination ───────────────────────────────────────

async def test_search_by_company(client: AsyncClient) -> None:
    await register_user(client)
    await _create_lead(client, company_name="Quantum Widgets", first_name="Zoe", last_name="Zephyr")
    await _create_lead(client, company_name="Acme Corp", first_name="Bo", last_name="Baker")

    response = await client.get("/api/v1/leads?search=quantum")
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["company_name"] == "Quantum Widgets"


async def test_filter_by_status_and_pagination(client: AsyncClient) -> None:
    await register_user(client)
    for i in range(5):
        await _create_lead(client, first_name=f"Lead{i}", email=unique_email(f"page{i}"))
    await _create_lead(client, first_name="Contacted", status="contacted", email=unique_email("contacted"))

    filtered = await client.get("/api/v1/leads?status=contacted")
    assert filtered.json()["meta"]["total"] == 1

    paged = await client.get("/api/v1/leads?page=1&page_size=3")
    assert len(paged.json()["data"]) == 3
    assert paged.json()["meta"]["total"] == 6


async def test_sort_by_name(client: AsyncClient) -> None:
    await register_user(client)
    await _create_lead(client, first_name="Zeta", email=unique_email("z"))
    await _create_lead(client, first_name="Alpha", email=unique_email("a"))

    response = await client.get("/api/v1/leads?sort_by=name&sort_desc=false")
    names = [item["first_name"] for item in response.json()["data"]]
    assert names.index("Alpha") < names.index("Zeta")


# ─── Notes ──────────────────────────────────────────────────────────────────────

async def test_note_crud(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    create = await client.post(f"/api/v1/leads/{lead['id']}/notes", json={"content": "Called them.", "is_pinned": False})
    assert create.status_code == 201
    note = create.json()["data"]
    assert note["author_name"] is not None

    update = await client.patch(
        f"/api/v1/leads/{lead['id']}/notes/{note['id']}", json={"content": "Called them, left voicemail.", "is_pinned": True}
    )
    assert update.status_code == 200
    assert update.json()["data"]["is_pinned"] is True

    listing = await client.get(f"/api/v1/leads/{lead['id']}/notes")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
    assert listing.json()["data"][0]["content"] == "Called them, left voicemail."

    delete = await client.delete(f"/api/v1/leads/{lead['id']}/notes/{note['id']}")
    assert delete.status_code == 200

    lead_after = await client.get(f"/api/v1/leads/{lead['id']}")
    assert lead_after.json()["data"]["notes_count"] == 0


# ─── Attachments ────────────────────────────────────────────────────────────────

async def test_attachment_upload_and_delete(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    upload = await client.post(
        f"/api/v1/leads/{lead['id']}/attachments",
        files={"file": ("proposal.pdf", io.BytesIO(b"%PDF-1.4 fake pdf content"), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    attachment = upload.json()["data"]
    assert attachment["filename"] == "proposal.pdf"
    assert attachment["file_url"].startswith("/media/organizations/")

    listing = await client.get(f"/api/v1/leads/{lead['id']}/attachments")
    assert len(listing.json()["data"]) == 1

    delete = await client.delete(f"/api/v1/leads/{lead['id']}/attachments/{attachment['id']}")
    assert delete.status_code == 200


async def test_attachment_rejects_unsupported_type(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    response = await client.post(
        f"/api/v1/leads/{lead['id']}/attachments",
        files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert response.status_code == 400


# ─── Bulk actions ───────────────────────────────────────────────────────────────

async def test_bulk_archive_and_restore(client: AsyncClient) -> None:
    await register_user(client)
    lead1 = await _create_lead(client, email=unique_email("bulk1"))
    lead2 = await _create_lead(client, email=unique_email("bulk2"))

    archive = await client.post(
        "/api/v1/leads/bulk", json={"lead_ids": [lead1["id"], lead2["id"]], "action": "archive"}
    )
    assert archive.status_code == 200
    body = archive.json()["data"]
    assert body["success_count"] == 2

    restore = await client.post(
        "/api/v1/leads/bulk", json={"lead_ids": [lead1["id"]], "action": "restore"}
    )
    assert restore.json()["data"]["success_count"] == 1


async def test_bulk_add_and_remove_tags(client: AsyncClient) -> None:
    await register_user(client)
    lead1 = await _create_lead(client, email=unique_email("t1"))
    lead2 = await _create_lead(client, email=unique_email("t2"))

    add = await client.post(
        "/api/v1/leads/bulk",
        json={"lead_ids": [lead1["id"], lead2["id"]], "action": "add_tags", "tags": ["Priority"]},
    )
    assert add.json()["data"]["success_count"] == 2

    lead1_after = await client.get(f"/api/v1/leads/{lead1['id']}")
    assert "Priority" in [t["name"] for t in lead1_after.json()["data"]["tags"]]


async def test_bulk_partial_failure_reports_errors(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client, email=unique_email("partial"))
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        "/api/v1/leads/bulk", json={"lead_ids": [lead["id"], fake_id], "action": "favorite"}
    )
    body = response.json()["data"]
    assert body["success_count"] == 1
    assert body["failed_count"] == 1


# ─── CSV import / export ────────────────────────────────────────────────────────

_CSV_CONTENT = (
    "Full Name,Email,Company,Job Title\n"
    "Grace Hopper,grace@example.com,Analytical Engines,Rear Admiral\n"
    "Alan Turing,alan@example.com,Bletchley Park,Codebreaker\n"
)


async def test_import_preview_auto_detects_mapping(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/leads/import",
        data={"mode": "preview"},
        files={"file": ("leads.csv", io.BytesIO(_CSV_CONTENT.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_rows"] == 2
    assert data["suggested_mapping"]["Email"] == "email"
    assert data["suggested_mapping"]["Company"] == "company_name"
    assert data["suggested_mapping"]["Full Name"] == "full_name"


async def test_import_commit_creates_leads(client: AsyncClient) -> None:
    import json

    await register_user(client)
    mapping = {"Full Name": "full_name", "Email": "email", "Company": "company_name", "Job Title": "job_title"}
    response = await client.post(
        "/api/v1/leads/import",
        data={"mode": "commit", "mapping": json.dumps(mapping)},
        files={"file": ("leads.csv", io.BytesIO(_CSV_CONTENT.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["successful_count"] == 2
    assert result["failed_count"] == 0

    listing = await client.get("/api/v1/leads?search=grace")
    assert listing.json()["meta"]["total"] == 1


async def test_import_commit_detects_duplicates(client: AsyncClient) -> None:
    import json

    await register_user(client)
    await _create_lead(client, first_name="Grace", last_name="Hopper", email="grace@example.com")

    mapping = {"Full Name": "full_name", "Email": "email", "Company": "company_name"}
    response = await client.post(
        "/api/v1/leads/import",
        data={"mode": "commit", "mapping": json.dumps(mapping)},
        files={"file": ("leads.csv", io.BytesIO(_CSV_CONTENT.encode()), "text/csv")},
    )
    result = response.json()["data"]
    assert result["duplicate_count"] == 1
    assert result["successful_count"] == 1


async def test_export_csv(client: AsyncClient) -> None:
    await register_user(client)
    await _create_lead(client, first_name="Export", last_name="Me", email=unique_email("export"))

    response = await client.get("/api/v1/leads/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Export" in response.text
    assert "attachment" in response.headers["content-disposition"]


async def test_export_selected_leads_only(client: AsyncClient) -> None:
    await register_user(client)
    lead1 = await _create_lead(client, first_name="Keep", email=unique_email("keep"))
    await _create_lead(client, first_name="Skip", email=unique_email("skip"))

    response = await client.get(f"/api/v1/leads/export?lead_ids={lead1['id']}")
    assert "Keep" in response.text
    assert "Skip" not in response.text


# ─── Permissions ────────────────────────────────────────────────────────────────

async def test_sales_role_cannot_delete_import_export_bulk(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    sales_client = await _invite_and_accept(client, db, owner_organization_id=org_id, role_name="sales")
    try:
        lead_response = await sales_client.post(
            "/api/v1/leads",
            json={"first_name": "Sales", "last_name": "Owned", "email": unique_email("sales")},
        )
        assert lead_response.status_code == 201
        lead_id = lead_response.json()["data"]["id"]

        assert (await sales_client.delete(f"/api/v1/leads/{lead_id}")).status_code == 403
        assert (await sales_client.get("/api/v1/leads/export")).status_code == 403
        assert (
            await sales_client.post("/api/v1/leads/bulk", json={"lead_ids": [lead_id], "action": "archive"})
        ).status_code == 403

        # But sales CAN add a note (notes.manage is granted).
        note_response = await sales_client.post(
            f"/api/v1/leads/{lead_id}/notes", json={"content": "Following up."}
        )
        assert note_response.status_code == 201
    finally:
        await sales_client.aclose()


async def test_viewer_cannot_create_leads(client: AsyncClient, db: AsyncSession) -> None:
    owner_body = await register_user(client)
    org_id = owner_body["data"]["organization_id"]
    viewer_client = await _invite_and_accept(client, db, owner_organization_id=org_id, role_name="viewer")
    try:
        response = await viewer_client.post(
            "/api/v1/leads", json={"first_name": "Nope", "email": unique_email("viewer")}
        )
        assert response.status_code == 403
    finally:
        await viewer_client.aclose()
