import pytest

from tests.conftest import csrf_headers, register_and_login

pytestmark = pytest.mark.asyncio


async def test_register_creates_user_and_session_cookies(client):
    data = await register_and_login(client)
    assert data["username"] == "alice"
    assert "ase_access_token" in client.cookies
    assert "ase_refresh_token" in client.cookies
    assert "ase_csrf_token" in client.cookies


async def test_cookie_samesite_is_configurable_for_cross_site_deployments(client, monkeypatch):
    # Netlify (frontend) + Render (backend) live on different domains, so cookies need
    # SameSite=None to be sent at all — this is what makes that topology possible.
    monkeypatch.setattr("app.auth.cookies.settings.cookie_samesite", "none")
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Cross Site",
            "username": "crosssite",
            "email": "crosssite@example.com",
            "password": "correcthorse1",
            "confirm_password": "correcthorse1",
        },
    )
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert set_cookie_headers, "expected Set-Cookie headers on register"
    assert all("samesite=none" in h.lower() for h in set_cookie_headers)


async def test_duplicate_registration_rejected(client):
    await register_and_login(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Alice Two",
            "username": "alice",
            "email": "someone-else@example.com",
            "password": "correcthorse1",
            "confirm_password": "correcthorse1",
        },
    )
    assert response.status_code == 409


async def test_login_with_wrong_password_fails(client):
    await register_and_login(client)
    response = await client.post(
        "/api/v1/auth/login", json={"username_or_email": "alice", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_me_requires_authentication(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client):
    await register_and_login(client)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


async def test_refresh_rotates_token_and_invalidates_old_one(client):
    await register_and_login(client)
    old_refresh = client.cookies.get("ase_refresh_token")

    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    new_refresh = client.cookies.get("ase_refresh_token")
    assert new_refresh != old_refresh

    # Replay the old refresh token: must be rejected since it was rotated out.
    client.cookies.set("ase_refresh_token", old_refresh, path="/api/v1/auth")
    replay = await client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401


async def test_logout_revokes_session(client):
    await register_and_login(client)
    response = await client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 204

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401


async def test_logout_without_csrf_header_is_rejected(client):
    await register_and_login(client)
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 403
