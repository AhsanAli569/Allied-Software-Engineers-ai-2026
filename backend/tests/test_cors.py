import pytest

pytestmark = pytest.mark.asyncio

# The test app is already constructed (app.main.app, imported once) with whatever
# CORS_ORIGINS was in backend/.env when the test process started — locally that's
# "http://localhost:3000" (see backend/.env.example). This validates the live
# CORSMiddleware behavior end-to-end, not just the settings-parsing logic in test_config.py.
ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "https://evil.example.com"


async def test_cors_preflight_allows_configured_origin(client):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_cors_preflight_rejects_unconfigured_origin(client):
    response = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": DISALLOWED_ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    # This is the exact symptom reported in production: no Access-Control-Allow-Origin
    # header at all for an origin that isn't in CORS_ORIGINS, which the browser then
    # reports as a generic, unhelpful CORS failure.
    assert "access-control-allow-origin" not in response.headers


async def test_cors_headers_present_on_actual_response_not_just_preflight(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "nobody", "password": "wrong"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert response.status_code == 401  # the CORS headers matter regardless of the outcome
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


async def test_options_preflight_is_not_blocked_by_csrf_or_auth(client):
    # A route that requires both auth and CSRF (state-changing, cookie-based) — the
    # preflight must still succeed without a session or CSRF token, because
    # CORSMiddleware answers OPTIONS directly and never reaches those dependencies.
    response = await client.options(
        "/api/v1/conversations",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
