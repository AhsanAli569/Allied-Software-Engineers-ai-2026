import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers._openai_compatible import REQUEST_TIMEOUT
from app.providers.base import AIProvider, ChatMessage, ChatResult
from app.providers.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _message_parts(message: ChatMessage) -> list[dict]:
    parts: list[dict] = [{"text": message.content}]
    for image in message.images or []:
        parts.append({"inline_data": {"mime_type": image.mime_type, "data": image.data_base64}})
    return parts


def _to_gemini_payload(messages: list[ChatMessage], params: dict[str, Any]) -> dict:
    system_parts = [m.content for m in messages if m.role == "system"]
    contents = [
        {"role": "model" if m.role == "assistant" else "user", "parts": _message_parts(m)}
        for m in messages
        if m.role != "system"
    ]
    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": params.get("temperature", 0.7),
            "maxOutputTokens": params.get("max_tokens", 2048),
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
    return payload


def _map_error(exc: Exception, name: str) -> Exception:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderTimeoutError(f"{name} request timed out")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return ProviderAuthError(f"{name} rejected the API key")
        if status == 429:
            return ProviderRateLimitError(f"{name} rate limit / quota exceeded")
        if status >= 500:
            return ProviderUnavailableError(f"{name} server error ({status})")
        return ProviderUnavailableError(f"{name} returned {status}")
    return ProviderUnavailableError(f"{name} request failed: {exc}")


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        self.name = "gemini"
        self.api_key = api_key
        # Reused across requests (cached by the factory, so effectively app-lifetime) —
        # avoids a fresh TCP+TLS handshake to Google on every single message.
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _require_key(self) -> str:
        if not self.api_key:
            raise ProviderAuthError("Gemini API key is not configured")
        return self.api_key

    async def chat(self, messages: list[ChatMessage], model: str, **params: Any) -> ChatResult:
        key = self._require_key()
        try:
            response = await self._client.post(
                f"{BASE_URL}/models/{model}:generateContent?key={key}",
                json=_to_gemini_payload(messages, params),
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return ChatResult(content=text, model=model, provider=self.name)
        except ProviderAuthError:
            raise
        except Exception as exc:
            raise _map_error(exc, self.name) from exc

    async def stream_chat(self, messages: list[ChatMessage], model: str, **params: Any) -> AsyncIterator[str]:
        key = self._require_key()
        try:
            async with self._client.stream(
                "POST",
                f"{BASE_URL}/models/{model}:streamGenerateContent?alt=sse&key={key}",
                json=_to_gemini_payload(messages, params),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if not data_str:
                        continue
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    candidates = chunk.get("candidates") or []
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text")
                        if text:
                            yield text
        except ProviderAuthError:
            raise
        except (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError):
            raise
        except Exception as exc:
            raise _map_error(exc, self.name) from exc

    async def health_check(self) -> bool:
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        if not self.api_key:
            return []
        try:
            response = await self._client.get(f"{BASE_URL}/models?key={self.api_key}", timeout=httpx.Timeout(10.0))
            response.raise_for_status()
            data = response.json()
            return [m["name"].removeprefix("models/") for m in data.get("models", [])]
        except Exception:
            return []
