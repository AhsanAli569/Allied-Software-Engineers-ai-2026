import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.middleware import rate_limit as rate_limit_module
from app.api.v1 import messages as messages_module


@pytest_asyncio.fixture
async def db_session():
    # Fresh isolated in-memory SQLite DB per test — fast, no external Postgres needed for
    # unit/integration tests. StaticPool keeps a single connection alive for the engine's
    # lifetime so the in-memory DB persists across the multiple sessions/requests a test
    # makes. Models use the cross-dialect GUID type so this stays faithful to the
    # production Postgres schema.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        yield session

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
def _reset_in_memory_state():
    rate_limit_module._hits.clear()
    messages_module._seen_idempotency_keys.clear()
    yield


@pytest_asyncio.fixture
async def client(db_session):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def csrf_headers(client: httpx.AsyncClient) -> dict:
    token = client.cookies.get("ase_csrf_token")
    return {"X-CSRF-Token": token} if token else {}


async def register_and_login(client: httpx.AsyncClient, *, username="alice", email="alice@example.com") -> dict:
    payload = {
        "full_name": "Alice Example",
        "username": username,
        "email": email,
        "password": "correcthorse1",
        "confirm_password": "correcthorse1",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
