import pytest

from app.models.ai_model import AIModel
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def _seed_two_models(db_session) -> None:
    db_session.add_all(
        [
            AIModel(model_id="m-gemini", display_name="Gemini Model", provider="gemini", active=True, priority=10),
            AIModel(model_id="m-groq", display_name="Groq Model", provider="groq", active=True, priority=20),
        ]
    )
    await db_session.commit()


async def test_models_requires_auth(client):
    response = await client.get("/api/v1/models")
    assert response.status_code == 401


async def test_models_reports_which_providers_are_configured(client, db_session, monkeypatch):
    await _seed_two_models(db_session)
    monkeypatch.setattr(
        "app.api.v1.models.is_provider_configured", lambda name: name == "groq"
    )

    await register_and_login(client)
    response = await client.get("/api/v1/models")
    assert response.status_code == 200

    by_id = {m["model_id"]: m for m in response.json()}
    assert by_id["m-gemini"]["configured"] is False
    assert by_id["m-groq"]["configured"] is True
