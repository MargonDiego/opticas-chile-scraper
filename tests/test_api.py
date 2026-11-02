import pytest
from httpx import AsyncClient, ASGITransport
from src.database import async_session_factory
from src.main import app
from src.models import Product
from src.services.ollama import ollama_service


@pytest.mark.asyncio
async def test_health_endpoint(monkeypatch):
    async def _ping_ok() -> bool:
        return True

    monkeypatch.setattr(ollama_service, "ping", _ping_ok)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["database"] == "ok"
        assert data["ollama"] == "ok"
        assert "gmo" in data["available_stores"]


@pytest.mark.asyncio
async def test_list_stores_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/stores")
        assert res.status_code == 200
        data = res.json()
        assert len(data["stores"]) == 7


@pytest.mark.asyncio
async def test_get_products_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/products")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_get_products_pagination_and_filtering():
    async with async_session_factory() as session:
        p1 = Product(
            id="gmo:prod-1",
            store="gmo",
            store_product_id="prod-1",
            brand="Ray-Ban",
            model_name="Aviator Classic",
            category="sol",
            url="https://gmo.cl/p1",
            current_price_normal=120000,
            current_price_discount=90000,
            current_in_stock=True,
        )
        p2 = Product(
            id="ryk:prod-2",
            store="ryk",
            store_product_id="prod-2",
            brand="Oakley",
            model_name="Holbrook",
            category="sol",
            url="https://ryk.cl/p2",
            current_price_normal=80000,
            current_price_discount=None,
            current_in_stock=True,
        )
        p3 = Product(
            id="gmo:prod-3",
            store="gmo",
            store_product_id="prod-3",
            brand="Vogue",
            model_name="CatEye",
            category="opticos",
            url="https://gmo.cl/p3",
            current_price_normal=45000,
            current_price_discount=None,
            current_in_stock=False,
        )
        session.add_all([p1, p2, p3])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Total count header and pagination
        res_all = await client.get("/api/products?limit=2&offset=0")
        assert res_all.status_code == 200
        assert res_all.headers.get("X-Total-Count") == "3"
        data_all = res_all.json()
        assert len(data_all) == 2

        # Offset page 2
        res_page2 = await client.get("/api/products?limit=2&offset=2")
        assert len(res_page2.json()) == 1

        # 2. Filter by store
        res_gmo = await client.get("/api/products?store=gmo")
        assert res_gmo.headers.get("X-Total-Count") == "2"
        for p in res_gmo.json():
            assert p["store"] == "gmo"

        # 3. Filter by stock
        res_stock = await client.get("/api/products?in_stock=true")
        assert res_stock.headers.get("X-Total-Count") == "2"

        # 4. Sorting price-asc
        res_sorted = await client.get("/api/products?sort_by=price-asc")
        prices = [p["current_price_discount"] or p["current_price_normal"] for p in res_sorted.json()]
        assert prices == sorted(prices)
