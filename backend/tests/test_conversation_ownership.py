import pytest

from tests.conftest import csrf_headers, register_and_login

pytestmark = pytest.mark.asyncio


async def test_user_cannot_read_another_users_conversation(client, db_session):
    import httpx

    from app.main import app

    # User A creates a conversation.
    await register_and_login(client, username="alice", email="alice@example.com")
    create_response = await client.post(
        "/api/v1/conversations", json={"title": "Alice's private chat"}, headers=csrf_headers(client)
    )
    assert create_response.status_code == 201
    conversation_id = create_response.json()["id"]

    # User B, a separate authenticated session, tries to access it directly by ID.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client_b:
        await register_and_login(client_b, username="bob", email="bob@example.com")

        get_response = await client_b.get(f"/api/v1/conversations/{conversation_id}")
        assert get_response.status_code == 404

        patch_response = await client_b.patch(
            f"/api/v1/conversations/{conversation_id}",
            json={"title": "hijacked"},
            headers=csrf_headers(client_b),
        )
        assert patch_response.status_code == 404

        delete_response = await client_b.delete(
            f"/api/v1/conversations/{conversation_id}", headers=csrf_headers(client_b)
        )
        assert delete_response.status_code == 404

        messages_response = await client_b.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert messages_response.status_code == 404

    # User A can still read their own conversation.
    own_response = await client.get(f"/api/v1/conversations/{conversation_id}")
    assert own_response.status_code == 200


async def test_conversation_list_only_returns_own_conversations(client):
    import httpx

    from app.main import app

    await register_and_login(client, username="alice", email="alice2@example.com")
    await client.post("/api/v1/conversations", json={"title": "Alice chat"}, headers=csrf_headers(client))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client_b:
        await register_and_login(client_b, username="bob", email="bob2@example.com")
        response = await client_b.get("/api/v1/conversations")
        assert response.status_code == 200
        assert response.json() == []
