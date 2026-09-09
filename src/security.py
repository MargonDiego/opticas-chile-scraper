import logging
import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from src.config import settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Validate incoming X-API-Key header against configured settings.API_KEY."""
    configured_key = settings.API_KEY

    # If no API key is set in config, allow access (or warn in logs)
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