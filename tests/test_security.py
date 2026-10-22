import pytest
from httpx import AsyncClient, ASGITransport
from starlette.requests import Request
from src.main import app
from src.config import settings
from src.security import IPRateLimiter


def _make_request(headers=None, client=("203.0.113.9", 51024)):
    """Build a minimal ASGI Request with the given headers and peer address.

    Follows the ASGI spec: headers are (name, value) byte pairs, and
    ``client`` is the (host, port) tuple set by the server.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/products",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": client,
    }
    return Request(scope)


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


def test_get_client_ip_ignores_forwarding_headers_when_trust_disabled(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "CF-Connecting-IP": "198.51.100.1",
            "X-Forwarded-For": "198.51.100.2",
            "X-Real-IP": "198.51.100.3",
        }
    )
    assert limiter._get_client_ip(request) == "203.0.113.9"


def test_get_client_ip_cf_connecting_ip_beats_spoofed_xff(monkeypatch):
    # Regression: a client rotating X-Forwarded-For leftmost values used to
    # get a fresh rate-limit bucket per request (measured in production: 25
    # unique XFF values, zero 429s). CF-Connecting-IP must win over that
    # attacker-controlled entry, on the expectation that Cloudflare overwrites
    # it -- which is what the post-deploy probe in security.py has to confirm.
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "CF-Connecting-IP": "192.0.2.10",
            "X-Forwarded-For": "10.0.0.5, 172.16.0.1",
        }
    )
    assert limiter._get_client_ip(request) == "192.0.2.10"


def test_get_client_ip_cf_connecting_ip_ipv6(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "CF-Connecting-IP": "2001:db8::1",
            "X-Forwarded-For": "10.0.0.5",
        }
    )
    assert limiter._get_client_ip(request) == "2001:db8::1"


@pytest.mark.parametrize(
    "bad_cf_ip",
    [
        "not-an-ip",
        "999.1.1.1",
        "x" * 512,
    ],
)
def test_get_client_ip_invalid_cf_connecting_ip_falls_through_to_xff(monkeypatch, bad_cf_ip):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "CF-Connecting-IP": bad_cf_ip,
            "X-Forwarded-For": "198.51.100.7, 10.0.0.1",
        }
    )
    assert limiter._get_client_ip(request) == "198.51.100.7"


def test_get_client_ip_invalid_xff_falls_through_to_real_ip_then_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()

    # Invalid XFF -> X-Real-IP (valid) is used
    request = _make_request(
        headers={
            "X-Forwarded-For": "not-an-ip",
            "X-Real-IP": "198.51.100.8",
        }
    )
    assert limiter._get_client_ip(request) == "198.51.100.8"

    # Invalid XFF AND invalid X-Real-IP -> peer host is used
    request = _make_request(
        headers={
            "X-Forwarded-For": "not-an-ip",
            "X-Real-IP": "also-not-an-ip",
        }
    )
    assert limiter._get_client_ip(request) == "203.0.113.9"


def test_get_client_ip_xff_leftmost_without_cf_header(monkeypatch):
    # Non-Cloudflare path: leftmost XFF entry is still honored.
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(headers={"X-Forwarded-For": "198.51.100.20, 10.0.0.1, 172.16.0.1"})
    assert limiter._get_client_ip(request) == "198.51.100.20"


def test_get_client_ip_no_headers_returns_peer_host(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request()
    assert limiter._get_client_ip(request) == "203.0.113.9"


def test_get_client_ip_no_client_returns_loopback(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(client=None)
    assert limiter._get_client_ip(request) == "127.0.0.1"


@pytest.mark.parametrize(
    "zone_ip",
    [
        "fe80::1%eth0",
        # ipaddress accepts an arbitrarily long scope suffix, which used to
        # let a client mint a multi-kilobyte rate-limit bucket key that
        # passed validation. Zone identifiers are never a real client address
        # in a forwarded header, so they are rejected outright.
        "fe80::1%" + ("z" * 4000),
        "fe80::1%25" + ("a" * 100),
    ],
)
def test_get_client_ip_ipv6_zone_id_is_rejected(monkeypatch, zone_ip):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "CF-Connecting-IP": zone_ip,
            "X-Forwarded-For": "198.51.100.44",
        }
    )
    # Zone id in CF-Connecting-IP falls through; valid XFF entry is used.
    assert limiter._get_client_ip(request) == "198.51.100.44"


def test_get_client_ip_zone_id_in_xff_falls_through_to_peer(monkeypatch):
    # Same guard on the XFF fallback path, which is the one reachable when
    # Cloudflare is absent or the CF header is unusable.
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    limiter = IPRateLimiter()
    request = _make_request(
        headers={
            "X-Forwarded-For": "fe80::1%" + ("z" * 300) + ", 10.0.0.1",
        }
    )
    assert limiter._get_client_ip(request) == "203.0.113.9"