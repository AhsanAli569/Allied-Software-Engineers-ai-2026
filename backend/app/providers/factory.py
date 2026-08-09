from functools import lru_cache

from app.config import get_settings
from app.providers.base import AIProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.openrouter import OpenRouterProvider

_PROVIDER_NAMES = {"gemini", "groq", "openrouter"}


@lru_cache
def _providers() -> dict[str, AIProvider]:
    settings = get_settings()
    return {
        "gemini": GeminiProvider(settings.gemini_api_key),
        "groq": GroqProvider(settings.groq_api_key),
        "openrouter": OpenRouterProvider(settings.openrouter_api_key),
    }


def get_provider(name: str) -> AIProvider:
    if name not in _PROVIDER_NAMES:
        raise ValueError(f"Unknown provider: {name}")
    return _providers()[name]


def is_provider_configured(name: str) -> bool:
    settings = get_settings()
    api_keys = {
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
        "openrouter": settings.openrouter_api_key,
    }
    return bool(api_keys.get(name))


async def close_all_providers() -> None:
    """Called on app shutdown to cleanly close the persistent httpx clients each provider
    holds (see OpenAICompatibleProvider/GeminiProvider — reused across requests for
    connection pooling, so they need an explicit close instead of a context manager).
    """
    if _providers.cache_info().currsize == 0:
        return
    for provider in _providers().values():
        aclose = getattr(provider, "aclose", None)
        if aclose:
            await aclose()
