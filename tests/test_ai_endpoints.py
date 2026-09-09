import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_semantic_search_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/products/search/semantic",
            json={"query": "lentes de sol ray ban", "limit": 5},
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_advisor_chat_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/advisor/chat",
            json={"message": "busco armazones ópticos para leer baratos"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "response" in data
        assert "relevant_products" in data