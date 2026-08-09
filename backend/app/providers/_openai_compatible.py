import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import AIProvider, ChatMessage, ChatResult
from app.providers.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


class OpenAICompatibleProvider(AIProvider):
    """Shared implementation for providers exposing an OpenAI-style /chat/completions
    endpoint (Groq, OpenRouter). Only base_url/api_key/headers differ between them.
    """

    def __init__(self, name: str, base_url: str, api_key: str, extra_headers: dict[str, str] | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.extra_headers = extra_headers or {}
        # One client reused for the provider's lifetime (it's cached by the factory, so this
        # is effectively app-lifetime). A fresh client per request meant a fresh TCP+TLS
        # handshake for every single message — this keeps the connection pooled/warm.
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderAuthError(f"{self.name} API key is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

    def _message_content(self, message: ChatMessage) -> str | list[dict]:
        if not message.images:
            return message.content
        parts: list[dict] = [{"type": "text", "text": message.content}]
        for image in message.images:
            parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{image.mime_type};base64,{image.data_base64}"}}
            )
        return parts

    def _payload(self, messages: list[ChatMessage], model: str, stream: bool, params: dict[str, Any]) -> dict:
        return {
            "model": model,
            "messages": [{"role": m.role, "content": self._message_content(m)} for m in messages],
            "stream": stream,
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 2048),
        }

    def _map_error(self, exc: Exception) -> Exception:
        if isinstance(exc, httpx.TimeoutException):
            return ProviderTimeoutError(f"{self.name} request timed out")
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 401 or status == 403:
                return ProviderAuthError(f"{self.name} rejected the API key")
            if status == 429:
                return ProviderRateLimitError(f"{self.name} rate limit exceeded")
            if status >= 500:
                return ProviderUnavailableError(f"{self.name} server error ({status})")
            return ProviderUnavailableError(f"{self.name} returned {status}")
        return ProviderUnavailableError(f"{self.name} request failed: {exc}")

    async def chat(self, messages: list[ChatMessage], model: str, **params: Any) -> ChatResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, model, stream=False, params=params),
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return ChatResult(content=content, model=model, provider=self.name)
        except ProviderAuthError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

    async def stream_chat(self, messages: list[ChatMessage], model: str, **params: Any) -> AsyncIterator[str]:
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, model, stream=True, params=params),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta
        except ProviderAuthError:
            raise
        except (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError):
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self.base_url}/models", headers=self._headers(), timeout=httpx.Timeout(5.0))
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            response = await self._client.get(f"{self.base_url}/models", headers=self._headers(), timeout=httpx.Timeout(10.0))
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []
