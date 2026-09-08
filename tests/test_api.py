import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "gmo" in data["available_stores"]


@pytest.mark.asyncio
async def test_list_stores_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/stores")
        assert res.status_code == 200
        data = res.json()
        assert len(data["stores"]) == 5


@pytest.mark.asyncio
async def test_get_products_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/products")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
