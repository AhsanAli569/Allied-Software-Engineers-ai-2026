import pytest

from tests.conftest import csrf_headers, register_and_login

pytestmark = pytest.mark.asyncio


async def test_update_full_name(client):
    await register_and_login(client)
    response = await client.patch("/api/v1/account", json={"full_name": "New Name"}, headers=csrf_headers(client))
    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"


async def test_account_update_requires_csrf(client):
    await register_and_login(client)
    response = await client.patch("/api/v1/account", json={"full_name": "New Name"})
    assert response.status_code == 403


async def test_change_password_requires_correct_current_password(client):
    await register_and_login(client)
    response = await client.post(
        "/api/v1/account/change-password",
        json={"current_password": "wrong-password", "new_password": "newpassword1"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 401


async def test_change_password_success_revokes_sessions_and_allows_new_login(client):
    await register_and_login(client)
    response = await client.post(
        "/api/v1/account/change-password",
        json={"current_password": "correcthorse1", "new_password": "newpassword1"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 204

    # Old session cookies must be invalidated by the password change.
    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401

    login_response = await client.post(
        "/api/v1/auth/login", json={"username_or_email": "alice", "password": "newpassword1"}
    )
    assert login_response.status_code == 200

    old_password_login = await client.post(
        "/api/v1/auth/login", json={"username_or_email": "alice", "password": "correcthorse1"}
    )
    assert old_password_login.status_code == 401


async def test_logout_all_revokes_every_session(client):
    import httpx

    from app.main import app

    await register_and_login(client)

    # A second "device" logs in as the same user.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as device_two:
        login_response = await device_two.post(
            "/api/v1/auth/login", json={"username_or_email": "alice", "password": "correcthorse1"}
        )
        assert login_response.status_code == 200

        await client.post("/api/v1/auth/logout-all", headers=csrf_headers(client))

        refresh_response = await device_two.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 401
