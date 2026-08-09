import base64

import pytest

from tests.conftest import csrf_headers, register_and_login

pytestmark = pytest.mark.asyncio

# Smallest valid 1x1 transparent PNG.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def _create_conversation(client) -> str:
    response = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    return response.json()["id"]


async def test_upload_valid_image(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "image"
    assert body["status"] == "ready"
    assert body["original_filename"] == "photo.png"


async def test_upload_rejects_content_that_does_not_match_extension(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("fake.png", b"this is not a png", "image/png")},
        headers=csrf_headers(client),
    )
    assert response.status_code == 400


async def test_upload_rejects_disallowed_extension(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("script.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=csrf_headers(client),
    )
    assert response.status_code == 400


async def test_upload_extracts_text_document(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("notes.txt", b"Payment is due on the 15th of each month.", "text/plain")},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["kind"] == "document"


async def test_list_and_delete_unattached_file(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    upload = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    listing = await client.get(f"/api/v1/conversations/{conv_id}/files")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    delete_response = await client.delete(f"/api/v1/conversations/{conv_id}/files/{file_id}", headers=csrf_headers(client))
    assert delete_response.status_code == 204

    listing_after = await client.get(f"/api/v1/conversations/{conv_id}/files")
    assert listing_after.json() == []


async def test_get_file_content_returns_bytes(client):
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    upload = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    content_response = await client.get(f"/api/v1/conversations/{conv_id}/files/{file_id}/content")
    assert content_response.status_code == 200
    assert content_response.content == PNG_BYTES
    assert content_response.headers["content-type"] == "image/png"


async def test_other_user_cannot_access_files(client, db_session):
    import httpx

    from app.main import app

    await register_and_login(client, username="owner3", email="owner3@example.com")
    conv_id = await _create_conversation(client)
    upload = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as intruder:
        await register_and_login(intruder, username="intruder3", email="intruder3@example.com")

        assert (await intruder.get(f"/api/v1/conversations/{conv_id}/files")).status_code == 404
        assert (await intruder.get(f"/api/v1/conversations/{conv_id}/files/{file_id}/content")).status_code == 404
        assert (
            await intruder.delete(f"/api/v1/conversations/{conv_id}/files/{file_id}", headers=csrf_headers(intruder))
        ).status_code == 404


async def test_max_attachments_per_conversation_enforced(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.files.settings.max_attachments_per_message", 2)
    await register_and_login(client)
    conv_id = await _create_conversation(client)

    for _ in range(2):
        r = await client.post(
            f"/api/v1/conversations/{conv_id}/files",
            files={"file": ("photo.png", PNG_BYTES, "image/png")},
            headers=csrf_headers(client),
        )
        assert r.status_code == 201

    over_limit = await client.post(
        f"/api/v1/conversations/{conv_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    assert over_limit.status_code == 400
