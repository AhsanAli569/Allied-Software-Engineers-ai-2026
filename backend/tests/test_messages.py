from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.models.ai_model import AIModel
from app.providers.base import AIProvider, ChatMessage, ChatResult
from tests.conftest import csrf_headers, register_and_login
from tests.test_files import PNG_BYTES

pytestmark = pytest.mark.asyncio


class ScriptedProvider(AIProvider):
    def __init__(self, name: str, reply: str = "Hello, I am ASE AI.", captured_calls: list | None = None):
        self.name = name
        self.reply = reply
        self.captured_calls = captured_calls

    async def chat(self, messages: list[ChatMessage], model: str, **params: Any) -> ChatResult:
        return ChatResult(content=self.reply, model=model, provider=self.name)

    async def stream_chat(self, messages: list[ChatMessage], model: str, **params: Any) -> AsyncIterator[str]:
        if self.captured_calls is not None:
            self.captured_calls.append(messages)
        for word in self.reply.split(" "):
            yield word + " "

    async def health_check(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return [self.name]


async def _seed_active_model(
    db_session, provider="fake", model_id="fake-model", vision_support: bool = False
) -> None:
    db_session.add(
        AIModel(
            model_id=model_id,
            display_name="Fake Model",
            provider=provider,
            active=True,
            priority=1,
            vision_support=vision_support,
        )
    )
    await db_session.commit()


async def test_send_message_streams_and_persists_assistant_reply(client, db_session, monkeypatch):
    await _seed_active_model(db_session)
    fake = ScriptedProvider("fake", reply="Hello there")
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: fake)

    await register_and_login(client)
    conv_response = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv_response.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "Hi ASE AI, who are you?"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert "event: start" in response.text
    assert "event: done" in response.text
    assert '"Hello "' in response.text
    assert '"there "' in response.text

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
    messages = history.json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Hi ASE AI, who are you?"
    assert messages[1]["content"] == "Hello there "
    assert messages[1]["provider"] == "fake"
    assert messages[1]["status"] == "complete"

    conv_after = await client.get(f"/api/v1/conversations/{conversation_id}")
    assert conv_after.json()["title"] == "Hi ASE AI, who are you?"


async def test_send_message_to_unowned_conversation_is_rejected(client, db_session, monkeypatch):
    import httpx

    from app.main import app

    await _seed_active_model(db_session)
    fake = ScriptedProvider("fake")
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: fake)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as owner_client:
        await register_and_login(owner_client, username="owner", email="owner@example.com")
        conv = await owner_client.post("/api/v1/conversations", json={}, headers=csrf_headers(owner_client))
        conversation_id = conv.json()["id"]

    await register_and_login(client, username="intruder", email="intruder@example.com")
    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "let me in"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 404


async def test_all_providers_unavailable_returns_friendly_error(client, monkeypatch):
    # No active models seeded — routing has nothing to try.
    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "hello?"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "No AI provider is currently available" in response.text


async def test_regenerate_creates_new_message_and_keeps_the_old_one(client, db_session, monkeypatch):
    await _seed_active_model(db_session)
    replies = iter(["First answer", "Second answer"])

    def get_provider(name):
        return ScriptedProvider("fake", reply=next(replies))

    monkeypatch.setattr("app.providers.router.get_provider", get_provider)

    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    first = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "What is 2+2?"},
        headers=csrf_headers(client),
    )
    assert '"First "' in first.text
    assert '"answer "' in first.text

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
    original_assistant = next(m for m in history.json() if m["role"] == "assistant")

    regenerate_response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/{original_assistant['id']}/regenerate",
        json={},
        headers=csrf_headers(client),
    )
    assert regenerate_response.status_code == 200
    assert '"Second "' in regenerate_response.text

    history_after = (await client.get(f"/api/v1/conversations/{conversation_id}/messages")).json()
    assistant_messages = [m for m in history_after if m["role"] == "assistant"]
    assert len(assistant_messages) == 2
    assert {m["content"] for m in assistant_messages} == {"First answer ", "Second answer "}
    regenerated = next(m for m in assistant_messages if m["content"] == "Second answer ")
    assert regenerated["regeneration_number"] == 1
    assert regenerated["parent_message_id"] == original_assistant["parent_message_id"]


async def test_regenerate_on_unowned_conversation_is_rejected(client, db_session, monkeypatch):
    import httpx

    from app.main import app

    await _seed_active_model(db_session)
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: ScriptedProvider("fake"))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as owner_client:
        await register_and_login(owner_client, username="owner2", email="owner2@example.com")
        conv = await owner_client.post("/api/v1/conversations", json={}, headers=csrf_headers(owner_client))
        conversation_id = conv.json()["id"]
        send = await owner_client.post(
            f"/api/v1/conversations/{conversation_id}/messages/stream",
            json={"content": "hi"},
            headers=csrf_headers(owner_client),
        )
        assert send.status_code == 200
        history = (await owner_client.get(f"/api/v1/conversations/{conversation_id}/messages")).json()
        assistant_id = next(m for m in history if m["role"] == "assistant")["id"]

    await register_and_login(client, username="intruder2", email="intruder2@example.com")
    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/{assistant_id}/regenerate",
        json={},
        headers=csrf_headers(client),
    )
    assert response.status_code == 404


async def test_document_attachment_text_is_included_in_provider_context(client, db_session, monkeypatch):
    await _seed_active_model(db_session)
    captured: list = []
    fake = ScriptedProvider("fake", reply="Got it", captured_calls=captured)
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: fake)

    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    upload = await client.post(
        f"/api/v1/conversations/{conversation_id}/files",
        files={"file": ("policy.txt", b"Refunds are processed within 14 business days.", "text/plain")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "What's the refund policy?", "attachment_ids": [file_id]},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert "event: done" in response.text

    assert len(captured) == 1
    last_message = captured[0][-1]
    assert "What's the refund policy?" in last_message.content
    assert "policy.txt" in last_message.content
    assert "Refunds are processed within 14 business days." in last_message.content

    # The attachment is now bound to the message it was sent with.
    history = (await client.get(f"/api/v1/conversations/{conversation_id}/messages")).json()
    user_message = next(m for m in history if m["role"] == "user")
    assert len(user_message["attachments"]) == 1
    assert user_message["attachments"][0]["original_filename"] == "policy.txt"


async def test_image_attachment_requires_vision_capable_model(client, db_session, monkeypatch):
    # Only a text-only model is active — sending an image should fail gracefully rather
    # than silently sending the image to a model that can't see it.
    await _seed_active_model(db_session, vision_support=False)
    fake = ScriptedProvider("fake")
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: fake)

    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    upload = await client.post(
        f"/api/v1/conversations/{conversation_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "What is this?", "attachment_ids": [file_id]},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "vision-capable" in response.text


async def test_image_attachment_routes_to_vision_capable_model(client, db_session, monkeypatch):
    await _seed_active_model(db_session, provider="text-only", model_id="text-model", vision_support=False)
    await _seed_active_model(db_session, provider="vision", model_id="vision-model", vision_support=True)

    captured: list = []
    text_provider = ScriptedProvider("text-only", reply="should not be used")
    vision_provider = ScriptedProvider("vision", reply="I see an image", captured_calls=captured)
    providers = {"text-only": text_provider, "vision": vision_provider}
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: providers[name])

    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    upload = await client.post(
        f"/api/v1/conversations/{conversation_id}/files",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "What is this?", "attachment_ids": [file_id]},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0][-1].images is not None
    assert captured[0][-1].images[0].mime_type == "image/png"

    history = (await client.get(f"/api/v1/conversations/{conversation_id}/messages")).json()
    assistant_message = next(m for m in history if m["role"] == "assistant")
    assert assistant_message["content"] == "I see an image "
    assert assistant_message["provider"] == "vision"


async def test_reusing_an_already_sent_attachment_is_rejected(client, db_session, monkeypatch):
    await _seed_active_model(db_session)
    fake = ScriptedProvider("fake")
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: fake)

    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    upload = await client.post(
        f"/api/v1/conversations/{conversation_id}/files",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=csrf_headers(client),
    )
    file_id = upload.json()["id"]

    first = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "first message", "attachment_ids": [file_id]},
        headers=csrf_headers(client),
    )
    assert first.status_code == 200

    # The file is now bound to that message and can't be deleted or reused.
    delete_response = await client.delete(
        f"/api/v1/conversations/{conversation_id}/files/{file_id}", headers=csrf_headers(client)
    )
    assert delete_response.status_code == 409

    second = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "second message", "attachment_ids": [file_id]},
        headers=csrf_headers(client),
    )
    assert second.status_code == 400


async def test_message_requires_content_or_attachment(client, db_session):
    await _seed_active_model(db_session)
    await register_and_login(client)
    conv = await client.post("/api/v1/conversations", json={}, headers=csrf_headers(client))
    conversation_id = conv.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "   "},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
