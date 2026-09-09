import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-XSS-Protection") == "1; mode=block"


@pytest.mark.asyncio
async def test_api_key_protection_when_configured():
    # Temporarily set API_KEY in settings
    original_key = settings.API_KEY
    settings.API_KEY = "test_super_secret_key_123"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health is always public
        res_health = await client.get("/api/health")
        assert res_health.status_code == 200

        # 2. Products without key -> 401
        res_unauth = await client.get("/api/products")
        assert res_unauth.status_code == 401

        # 3. Products with wrong key -> 403
        res_forbidden = await client.get("/api/products", headers={"X-API-Key": "wrong_key"})
        assert res_forbidden.status_code == 403

        # 4. Products with valid key -> 200
        res_auth = await client.get("/api/products", headers={"X-API-Key": "test_super_secret_key_123"})
        assert res_auth.status_code == 200

    settings.API_KEY = original_key