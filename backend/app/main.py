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
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

register_error_handlers(app)
app.include_router(api_router)
