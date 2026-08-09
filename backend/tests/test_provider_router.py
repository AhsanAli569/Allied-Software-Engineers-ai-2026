from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.models.ai_model import AIModel
from app.providers.base import AIProvider, ChatMessage, ChatResult
from app.providers.exceptions import AllProvidersExhaustedError, ProviderMidStreamError, ProviderRateLimitError
from app.providers.router import stream_chat_with_fallback

pytestmark = pytest.mark.asyncio


class FakeProvider(AIProvider):
    """A scripted provider: raises before yielding anything, fails mid-stream, or succeeds."""

    def __init__(self, name: str, behavior: str, chunks: list[str] | None = None):
        self.name = name
        self.behavior = behavior
        self.chunks = chunks or ["hello", " world"]

    async def chat(self, messages: list[ChatMessage], model: str, **params: Any) -> ChatResult:
        raise NotImplementedError

    async def stream_chat(self, messages: list[ChatMessage], model: str, **params: Any) -> AsyncIterator[str]:
        if self.behavior == "fail_before_first_chunk":
            raise ProviderRateLimitError(f"{self.name} rate limited")
        if self.behavior == "fail_mid_stream":
            yield self.chunks[0]
            raise ProviderRateLimitError(f"{self.name} rate limited mid-stream")
        for chunk in self.chunks:
            yield chunk

    async def health_check(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return [self.name]


def _model(provider: str, model_id: str, priority: int) -> AIModel:
    return AIModel(model_id=model_id, display_name=model_id, provider=provider, priority=priority)


async def test_falls_back_to_next_provider_when_primary_rate_limited(monkeypatch):
    primary = FakeProvider("primary", "fail_before_first_chunk")
    secondary = FakeProvider("secondary", "success", chunks=["fallback", " worked"])

    providers = {"primary": primary, "secondary": secondary}
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: providers[name])

    candidates = [_model("primary", "model-a", 1), _model("secondary", "model-b", 2)]
    selected: dict[str, str] = {}

    chunks = []
    async for chunk in stream_chat_with_fallback(
        candidates, [ChatMessage(role="user", content="hi")], lambda m, p: selected.update(model=m, provider=p)
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "fallback worked"
    assert selected == {"model": "model-b", "provider": "secondary"}


async def test_all_providers_exhausted_raises_and_does_not_loop_forever(monkeypatch):
    primary = FakeProvider("primary", "fail_before_first_chunk")
    secondary = FakeProvider("secondary", "fail_before_first_chunk")

    providers = {"primary": primary, "secondary": secondary}
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: providers[name])

    candidates = [_model("primary", "model-a", 1), _model("secondary", "model-b", 2)]

    with pytest.raises(AllProvidersExhaustedError) as exc_info:
        async for _ in stream_chat_with_fallback(candidates, [ChatMessage(role="user", content="hi")], lambda m, p: None):
            pass

    assert set(exc_info.value.attempts.keys()) == {"primary:model-a", "secondary:model-b"}


async def test_mid_stream_failure_does_not_silently_switch_providers(monkeypatch):
    primary = FakeProvider("primary", "fail_mid_stream", chunks=["partial"])
    secondary = FakeProvider("secondary", "success")

    providers = {"primary": primary, "secondary": secondary}
    monkeypatch.setattr("app.providers.router.get_provider", lambda name: providers[name])

    candidates = [_model("primary", "model-a", 1), _model("secondary", "model-b", 2)]
    chunks = []

    with pytest.raises(ProviderMidStreamError):
        async for chunk in stream_chat_with_fallback(
            candidates, [ChatMessage(role="user", content="hi")], lambda m, p: None
        ):
            chunks.append(chunk)

    # The partial chunk from the committed provider was already yielded — we must not have
    # silently spliced in output from the secondary provider afterwards.
    assert chunks == ["partial"]
