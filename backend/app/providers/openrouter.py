from app.providers._openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str):
        super().__init__(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            extra_headers={
                "HTTP-Referer": "https://ai.alliedsoftwareengineers.com",
                "X-Title": "ASE AI",
            },
        )
