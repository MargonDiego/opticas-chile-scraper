import logging
import secrets
import time
from collections import defaultdict
from typing import Optional
from fastapi import HTTPException, Request, Response, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Validate incoming X-API-Key header against configured settings.API_KEY."""
    configured_key = settings.API_KEY

    # If no API key is set in config, allow access
    if not configured_key or not configured_key.strip():
        return "unprotected"

    if not api_key:
        logger.warning("Unauthorized access attempt: missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-API-Key' authentication header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use constant-time comparison to protect against timing attacks
    if not secrets.compare_digest(api_key.strip(), configured_key.strip()):
        logger.warning("Unauthorized access attempt: invalid X-API-Key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid 'X-API-Key' provided",
        )

    return api_key


async def get_admin_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Validate incoming X-API-Key header against settings.ADMIN_API_KEY.

    Does NOT fall back to settings.API_KEY: that key is distributed to the
    public frontend bundle, so reusing it here would let any site visitor
    reach admin-only routes (scrape trigger, job listing, exports).
    """
    configured_admin_key = settings.ADMIN_API_KEY

    if not configured_admin_key or not configured_admin_key.strip():
        if settings.ENVIRONMENT == "production":
            logger.error("ADMIN_API_KEY is not configured in production - denying admin access")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin API is not configured",
            )
        return "unprotected"

    if not api_key:
        logger.warning("Unauthorized admin access attempt: missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-API-Key' admin authentication header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not secrets.compare_digest(api_key.strip(), configured_admin_key.strip()):
        logger.warning("Unauthorized admin access attempt: invalid admin API key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid administrative credentials",
        )

    return api_key


class IPRateLimiter:
    """Thread-safe, sliding-window in-memory IP rate limiter."""

    def __init__(self):
        self._public_history: dict[str, list[float]] = defaultdict(list)
        self._ai_history: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        # Only trust proxy-supplied headers when explicitly running behind a
        # trusted reverse proxy (Coolify/Traefik/nginx). Otherwise these
        # headers are attacker-controlled and let anyone spoof a new "IP" on
        # every request to bypass the rate limit entirely.
        if settings.TRUST_PROXY_HEADERS:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"

    def check(self, request: Request) -> tuple[bool, int, int]:
        """
        Evaluates rate limits by route type.
        Returns (is_allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        if not settings.ENABLE_RATE_LIMITING:
            return True, 999, 0

        path = request.url.path
        is_ai_route = path.startswith("/api/advisor") or path.startswith("/api/products/search/semantic")
        max_limit = settings.RATE_LIMIT_AI_PER_MINUTE if is_ai_route else settings.RATE_LIMIT_PUBLIC_PER_MINUTE
        window_seconds = 60

        now = time.time()
        ip = self._get_client_ip(request)
        history_map = self._ai_history if is_ai_route else self._public_history
        history = history_map[ip]

        # Purge expired timestamps
        cutoff = now - window_seconds
        valid = [t for t in history if t > cutoff]

        if len(valid) >= max_limit:
            retry_after = int(window_seconds - (now - valid[0])) + 1
            history_map[ip] = valid
            return False, 0, max(1, retry_after)

        valid.append(now)
        history_map[ip] = valid
        remaining = max_limit - len(valid)
        return True, remaining, 0


rate_limiter = IPRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for IP-based Rate Limiting (DDoS & AI saturation protection)."""

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API routes, allow static files / docs / healthcheck
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            allowed, remaining, retry_after = rate_limiter.check(request)
            if not allowed:
                logger.warning(f"Rate limit exceeded for client IP: {request.client.host if request.client else 'unknown'} on path {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(
                            settings.RATE_LIMIT_AI_PER_MINUTE
                            if request.url.path.startswith("/api/advisor")
                            else settings.RATE_LIMIT_PUBLIC_PER_MINUTE
                        ),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        response: Response = await call_next(request)
        return response