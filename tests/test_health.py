import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from src.database import get_session
from src.main import app
from src.services.ollama import ollama_service


class _UnreachableSession:
    """Minimal AsyncSession stand-in whose SELECT 1 blows up."""

    async def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError("connection refused"))


async def _unreachable_session():
    yield _UnreachableSession()


async def _get_health(**kwargs):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/api/health", **kwargs)


@pytest.mark.asyncio
async def test_health_reports_healthy_when_database_and_ollama_work(monkeypatch):
    async def _ping_ok() -> bool:
        return True

    monkeypatch.setattr(ollama_service, "ping", _ping_ok)

    res = await _get_health()

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["database"] == "ok"
    assert body["ollama"] == "ok"
    # Backwards-compatible fields kept for the frontend and Docker probes.
    assert body["environment"]
    assert body["security"] in {"api_key_enabled", "open_access"}
    assert "gmo" in body["available_stores"]


@pytest.mark.asyncio
async def test_health_reports_degraded_when_ollama_is_unreachable(monkeypatch):
    async def _ping_down() -> bool:
        return False

    monkeypatch.setattr(ollama_service, "ping", _ping_down)

    res = await _get_health()

    # Ollama being down must not fail the container healthcheck.
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "degraded"
    assert body["database"] == "ok"
    assert body["ollama"] == "unreachable"


@pytest.mark.asyncio
async def test_health_caches_probe_results_between_rapid_hits(monkeypatch):
    probe_calls: list[str] = []

    async def _ping_ok() -> bool:
        probe_calls.append("ping")
        return True

    monkeypatch.setattr(ollama_service, "ping", _ping_ok)

    first = await _get_health()
    second = await _get_health()

    # /api/health is public and exempt from the rate limiter: repeated hits
    # inside the TTL must not re-probe the database or Ollama.
    assert len(probe_calls) == 1
    for res in (first, second):
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_returns_503_when_database_is_unreachable(monkeypatch):
    probe_calls: list[str] = []

    async def _should_not_be_called() -> bool:
        probe_calls.append("ping")
        return True

    monkeypatch.setattr(ollama_service, "ping", _should_not_be_called)
    app.dependency_overrides[get_session] = _unreachable_session
    try:
        res = await _get_health()
    finally:
        app.dependency_overrides.pop(get_session, None)

    # Asserted after the request on purpose: raising inside the handler would be
    # swallowed by the endpoint's broad exception handling, so a flag is the only
    # way this test can actually fail if the probe order is inverted.
    assert probe_calls == [], "ollama must not be probed once the database is down"

    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "unhealthy"
    assert body["database"] == "unreachable"
    assert body["database_error"] == "OperationalError"
    # Only the error class is exposed, never the raw message or DSN.
    assert "connection refused" not in res.text
