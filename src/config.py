from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Cybersecurity & Authentication
    API_KEY: Optional[str] = None
    ADMIN_API_KEY: Optional[str] = None
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 120
    RATE_LIMIT_AI_PER_MINUTE: int = 20
    CORS_ORIGINS: Union[List[str], str] = ["*"]
    ENABLE_SECURITY_HEADERS: bool = True
    # Only enable when a reverse proxy (Coolify/Traefik/nginx) sits in front
    # and is known to overwrite X-Forwarded-For/X-Real-IP on every request.
    TRUST_PROXY_HEADERS: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/opticas.db"

    # Scraper Settings
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    SCRAPER_TIMEOUT_SECONDS: int = 30
    SCRAPER_MAX_CONCURRENCY: int = 5
    SCRAPER_RETRY_ATTEMPTS: int = 3
    AUTO_SCRAPE_INTERVAL_HOURS: int = 12

    # Spider Engine
    SPIDER_API_KEY: Optional[str] = None
    SPIDER_HOST: str = "http://localhost:3030"

    # Ollama Service
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "qwen2.5:1.5b"
    EMBEDDING_DIMENSION: int = 768

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

if settings.ENVIRONMENT == "production" and not (settings.API_KEY and settings.API_KEY.strip()):
    raise RuntimeError(
        "API_KEY must be set when ENVIRONMENT=production. "
        "Refusing to start in unprotected mode."
    )