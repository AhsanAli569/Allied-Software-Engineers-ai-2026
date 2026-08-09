from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ASE AI"
    environment: str = "development"
    debug: bool = True
    cors_origins: str = "http://localhost:3000"
    # Alternate/additional way to specify the allowed frontend origin — some hosts (Render
    # included) commonly use FRONTEND_URL by convention. If set, it's added to whatever
    # CORS_ORIGINS already has rather than replacing it, so either name (or both) works.
    frontend_url: str = ""
    # Explicit override only. Leave unset in normal deployments — cookie_samesite_effective
    # below derives the right value from `environment` automatically, so a cross-domain
    # deployment (Netlify + Render) doesn't silently break just because this one extra env
    # var was never set alongside ENVIRONMENT=production.
    cookie_samesite: str | None = None

    database_url: str = "postgresql+asyncpg://ase_ai:changeme@localhost:5432/ase_ai"

    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    rate_limit_auth_per_minute: int = 10
    rate_limit_chat_per_minute: int = 30
    rate_limit_upload_per_minute: int = 20

    storage_dir: str = "./storage"
    max_image_size_mb: int = 10
    max_document_size_mb: int = 20
    max_attachments_per_message: int = 5

    @property
    def cookie_samesite_effective(self) -> str:
        # "lax" works for same-origin deployments (a VPS behind one nginx, or local dev via
        # the Vite proxy). "none" is required once frontend and backend are on different
        # domains (Netlify + Render) — otherwise the browser drops the auth cookie on every
        # cross-site request, which looks like a 401 on /auth/me even right after a
        # successful login. Explicit COOKIE_SAMESITE still wins if someone sets it.
        if self.cookie_samesite:
            return self.cookie_samesite
        return "none" if self.environment == "production" else "lax"

    @property
    def cors_origin_list(self) -> list[str]:
        raw_values = self.cors_origins.split(",")
        if self.frontend_url:
            raw_values.append(self.frontend_url)

        origins: list[str] = []
        for value in raw_values:
            # Browsers send the Origin header with no trailing slash, so a stray trailing
            # slash in the env var (e.g. "https://ai.alliedsoftwareengineers.com/") would
            # otherwise never match and CORS would silently fail — the exact symptom this
            # is guarding against.
            origin = value.strip().rstrip("/")
            if origin and origin not in origins:
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
