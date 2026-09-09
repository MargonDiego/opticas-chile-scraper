from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database: Default SQLite for local dev/test; PostgreSQL+asyncpg with pgvector in Docker
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

    # Ollama Service (Homelab / Coolify)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "qwen2.5:1.5b"
    EMBEDDING_DIMENSION: int = 768

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()