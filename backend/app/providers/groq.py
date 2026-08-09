from app.providers._openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str):
        super().__init__(name="groq", base_url="https://api.groq.com/openai/v1", api_key=api_key)
