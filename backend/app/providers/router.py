import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.models.ai_model import AIModel
from app.providers.base import ChatMessage
from app.providers.exceptions import (
    AllProvidersExhaustedError,
    ProviderAuthError,
    ProviderMidStreamError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.factory import get_provider

logger = logging.getLogger("ase_ai.provider_router")

RETRYABLE = (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError, ProviderAuthError)
# Only rate-limit/timeout/unavailable get a small backoff — those are real services that
# might be momentarily overloaded. ProviderAuthError (bad/missing key) is a local config
# fact that won't change between now and the next line of code, so waiting before moving
# to the next candidate would just be pure added latency for no benefit.
BACKOFF_ELIGIBLE = (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError)
BACKOFF_SECONDS = 0.3
MAX_BACKOFF_SECONDS = 2.0


async def stream_chat_with_fallback(
    candidates: list[AIModel],
    messages: list[ChatMessage],
    on_provider_selected: Callable[[str, str], None],
    **params: Any,
) -> AsyncIterator[str]:
    """Try each candidate model/provider in priority order. Falls back on rate-limit,
    timeout, or unavailable errors *before* any content has been sent to the client.
    Never retries indefinitely — each candidate is tried at most once, with a small capped
    backoff only when the failure reason suggests waiting could plausibly help.
    """
    if not candidates:
        raise AllProvidersExhaustedError({"_": "no active models configured"})

    errors: dict[str, str] = {}
    backoff_attempt = 0

    for idx, model in enumerate(candidates):
        candidate_key = f"{model.provider}:{model.model_id}"
        provider = get_provider(model.provider)
        generator = provider.stream_chat(messages, model.model_id, **params)

        try:
            first_chunk = await generator.__anext__()
        except StopAsyncIteration:
            first_chunk = None
        except RETRYABLE as exc:
            # The reason goes directly in the message, not just `extra` — the default
            # logging formatter (as configured by uvicorn) silently drops `extra` fields,
            # which made real failures (e.g. a quota/auth problem with a provider) invisible
            # in the logs and left only the generic "no provider available" client message.
            logger.warning(
                "provider_failed candidate=%s error=%s", candidate_key, exc, extra={"candidate": candidate_key, "error": str(exc)}
            )
            errors[candidate_key] = str(exc)
            if idx < len(candidates) - 1 and isinstance(exc, BACKOFF_ELIGIBLE):
                await asyncio.sleep(min(BACKOFF_SECONDS * (2**backoff_attempt), MAX_BACKOFF_SECONDS))
                backoff_attempt += 1
            continue

        logger.info("provider_selected candidate=%s", candidate_key, extra={"candidate": candidate_key})
        on_provider_selected(model.model_id, model.provider)

        if first_chunk:
            yield first_chunk

        try:
            async for chunk in generator:
                yield chunk
        except RETRYABLE as exc:
            raise ProviderMidStreamError(str(exc)) from exc
        return

    raise AllProvidersExhaustedError(errors)
