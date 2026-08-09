from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio


def _years_ago(years: int, days_offset: int = 0) -> date:
    today = date.today()
    try:
        base = today.replace(year=today.year - years)
    except ValueError:
        # today is Feb 29 and the target year isn't a leap year
        base = today.replace(month=2, day=28, year=today.year - years)
    return base + timedelta(days=days_offset)


def _register_payload(date_of_birth: str, username: str = "agetest") -> dict:
    return {
        "full_name": "Age Test",
        "username": username,
        "email": f"{username}@example.com",
        "password": "correcthorse1",
        "confirm_password": "correcthorse1",
        "date_of_birth": date_of_birth,
    }


async def test_exactly_18_years_old_today_is_allowed(client):
    response = await client.post(
        "/api/v1/auth/register", json=_register_payload(_years_ago(18).isoformat(), "exactly18")
    )
    assert response.status_code == 201, response.text


async def test_well_over_18_is_allowed(client):
    response = await client.post(
        "/api/v1/auth/register", json=_register_payload(_years_ago(30).isoformat(), "over18")
    )
    assert response.status_code == 201, response.text


async def test_still_17_turning_18_tomorrow_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/register",
        json=_register_payload(_years_ago(18, days_offset=1).isoformat(), "almost18"),
    )
    assert response.status_code == 422
    assert "18" in response.text


async def test_17_years_old_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/register", json=_register_payload(_years_ago(17).isoformat(), "seventeen")
    )
    assert response.status_code == 422
    assert "18" in response.text


async def test_child_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/register", json=_register_payload(_years_ago(10).isoformat(), "child")
    )
    assert response.status_code == 422


async def test_future_date_of_birth_is_rejected(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = await client.post("/api/v1/auth/register", json=_register_payload(tomorrow, "future"))
    assert response.status_code == 422
    assert "future" in response.text.lower()


async def test_missing_date_of_birth_is_rejected(client):
    payload = _register_payload(_years_ago(30).isoformat(), "nodob")
    del payload["date_of_birth"]
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


async def test_rejected_registration_does_not_create_an_account(client):
    payload = _register_payload(_years_ago(10).isoformat(), "notcreated")
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

    # The username must still be available — no partial/leftover account from the rejected attempt.
    retry = await client.post(
        "/api/v1/auth/register", json=_register_payload(_years_ago(30).isoformat(), "notcreated")
    )
    assert retry.status_code == 201
