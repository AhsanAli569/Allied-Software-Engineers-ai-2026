import logging
from contextlib import asynccontextmanager

import truststore

# Must run before anything creates an SSL context (e.g. an httpx client making a provider
# call). Makes Python verify TLS certs against the OS trust store instead of certifi's
# bundled list — needed on machines where antivirus/security software does HTTPS
# inspection with a locally-installed root CA that only the OS store knows about.
truststore.inject_into_ssl()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1.router import api_router  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.middleware.error_handler import register_error_handlers  # noqa: E402
from app.providers.factory import close_all_providers  # noqa: E402

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_all_providers()


app = FastAPI(
    title=settings.app_name,
    description="Allied Software Engineers Artificial Intelligence — backend API",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Never "*" here — allow_credentials=True requires explicit origins; the CORS spec
    # (and browsers) reject a wildcard origin combined with credentialed requests outright.
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Custom response headers are invisible to cross-origin JS (response.headers.get(...))
    # unless explicitly exposed — without this, the frontend could never read the
    # X-CSRF-Token header that auth endpoints send back (see api/v1/auth.py).
    expose_headers=["X-CSRF-Token"],
)

register_error_handlers(app)
app.include_router(api_router)
