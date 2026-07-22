"""
Phase X Issue 07 -> Manual (non-AI) Email Templates: create/duplicate/edit/
delete/preview a hand-written template through the same `EmailTemplate`
table AI-generated templates already use, without disturbing that existing
flow. `template_type` doubles as "category".
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


async def _create_template(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": "Cold outreach v1", "template_type": "cold_outreach", "tone": "professional",
        "subject": "Quick question, {{ lead.first_name }}",
        "body_html": "<p>Hi {{ lead.first_name }},</p><p>...</p>",
        "body_text": "Hi {{ lead.first_name }},\n...",
        "variables_used": ["lead.first_name"],
        **overrides,
    }
    return await client.post("/api/v1/email-templates", json=payload)


async def test_create_manual_template(client: AsyncClient) -> None:
    await register_user(client)
    response = await _create_template(client)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["name"] == "Cold outreach v1"
    assert data["is_ai_generated"] is False
    assert data["ai_job_id"] is None
    assert data["variables_used"] == ["lead.first_name"]


async def test_create_manual_template_rejects_unsupported_type(client: AsyncClient) -> None:
    await register_user(client)
    response = await _create_template(client, template_type="not_a_real_type")
    assert response.status_code == 422


async def test_create_manual_template_requires_subject_and_body(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/email-templates", json={"name": "Bad", "template_type": "custom", "subject": "", "body_html": ""}
    )
    assert response.status_code == 422


async def test_manual_template_appears_in_list_and_is_editable(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_template(client)
    template_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/email-templates")
    assert any(t["id"] == template_id for t in listed.json()["data"])

    updated = await client.patch(f"/api/v1/email-templates/{template_id}", json={"name": "Renamed", "is_active": False})
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["name"] == "Renamed"
    assert updated.json()["data"]["is_active"] is False
    assert updated.json()["data"]["version"] == 2  # existing version-bump-on-update behavior preserved


async def test_duplicate_template_copies_content_as_new_independent_row(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_template(client)
    template_id = created.json()["data"]["id"]

    duplicated = await client.post(f"/api/v1/email-templates/{template_id}/duplicate", json={})
    assert duplicated.status_code == 201, duplicated.text
    copy = duplicated.json()["data"]
    assert copy["id"] != template_id
    assert copy["name"] == "Cold outreach v1 (copy)"
    assert copy["subject"] == "Quick question, {{ lead.first_name }}"
    assert copy["is_ai_generated"] is False

    # Editing the copy must not affect the original.
    await client.patch(f"/api/v1/email-templates/{copy['id']}", json={"name": "Edited copy"})
    original = await client.get(f"/api/v1/email-templates/{template_id}")
    assert original.json()["data"]["name"] == "Cold outreach v1"


async def test_duplicate_template_accepts_custom_name(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_template(client)
    template_id = created.json()["data"]["id"]
    duplicated = await client.post(f"/api/v1/email-templates/{template_id}/duplicate", json={"name": "My custom copy"})
    assert duplicated.json()["data"]["name"] == "My custom copy"


async def test_delete_manual_template(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_template(client)
    template_id = created.json()["data"]["id"]
    deleted = await client.delete(f"/api/v1/email-templates/{template_id}")
    assert deleted.status_code == 200, deleted.text
    missing = await client.get(f"/api/v1/email-templates/{template_id}")
    assert missing.status_code == 404


async def test_manual_templates_scoped_to_organization(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_template(client)
    template_id = created.json()["data"]["id"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    cross_org = await other_client.get(f"/api/v1/email-templates/{template_id}")
    assert cross_org.status_code == 404
    cross_org_duplicate = await other_client.post(f"/api/v1/email-templates/{template_id}/duplicate", json={})
    assert cross_org_duplicate.status_code == 404
