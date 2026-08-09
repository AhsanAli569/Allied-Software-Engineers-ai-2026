import pytest

pytestmark = pytest.mark.asyncio


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready(client):
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
