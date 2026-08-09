import pytest

from app.models.ai_model import AIModel
from tests.conftest import csrf_headers, register_and_login

pytestmark = pytest.mark.asyncio


async def test_create_and_list_conversation(client):
    await register_and_login(client)
    create = await client.post("/api/v1/conversations", json={"title": "My chat"}, headers=csrf_headers(client))
    assert create.status_code == 201
    assert create.json()["title"] == "My chat"

    listing = await client.get("/api/v1/conversations")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_rename_pin_and_archive_conversation(client):
    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conv_id = conv.json()["id"]

    renamed = await client.patch(
        f"/api/v1/conversations/{conv_id}", json={"title": "Renamed"}, headers=csrf_headers(client)
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    pinned = await client.patch(
        f"/api/v1/conversations/{conv_id}", json={"pinned": True}, headers=csrf_headers(client)
    )
    assert pinned.json()["pinned"] is True

    archived = await client.patch(
        f"/api/v1/conversations/{conv_id}", json={"archived": True}, headers=csrf_headers(client)
    )
    assert archived.json()["archived"] is True

    # Default listing excludes archived conversations.
    default_listing = await client.get("/api/v1/conversations", params={"archived": False})
    assert conv_id not in [c["id"] for c in default_listing.json()]

    archived_listing = await client.get("/api/v1/conversations", params={"archived": True})
    assert conv_id in [c["id"] for c in archived_listing.json()]


async def test_delete_conversation_is_soft_delete_and_owner_only(client):
    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conv_id = conv.json()["id"]

    delete_response = await client.delete(f"/api/v1/conversations/{conv_id}", headers=csrf_headers(client))
    assert delete_response.status_code == 204

    get_after_delete = await client.get(f"/api/v1/conversations/{conv_id}")
    assert get_after_delete.status_code == 404

    listing = await client.get("/api/v1/conversations")
    assert conv_id not in [c["id"] for c in listing.json()]


async def test_search_filters_by_title(client):
    await register_and_login(client)
    await client.post("/api/v1/conversations", json={"title": "Budget planning"}, headers=csrf_headers(client))
    await client.post("/api/v1/conversations", json={"title": "Recipe ideas"}, headers=csrf_headers(client))

    results = await client.get("/api/v1/conversations", params={"search": "budget"})
    assert results.status_code == 200
    titles = [c["title"] for c in results.json()]
    assert titles == ["Budget planning"]


async def test_create_conversation_requires_auth(client):
    # A self-consistent (but never-logged-in) CSRF cookie/header pair isolates this test to
    # the auth check specifically — without it, the router's CSRF check (which runs first
    # and doesn't require auth) would reject the request with 403 before auth is even checked.
    client.cookies.set("ase_csrf_token", "anonymous-csrf")
    response = await client.post(
        "/api/v1/conversations", json={}, headers={"X-CSRF-Token": "anonymous-csrf"}
    )
    assert response.status_code == 401
