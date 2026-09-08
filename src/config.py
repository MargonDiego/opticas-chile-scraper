from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite+aiosqlite:///data/opticas.db"

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    SCRAPER_TIMEOUT_SECONDS: int = 30
    SCRAPER_MAX_CONCURRENCY: int = 5
    SCRAPER_RETRY_ATTEMPTS: int = 3
    AUTO_SCRAPE_INTERVAL_HOURS: int = 12

    SPIDER_API_KEY: Optional[str] = None
    SPIDER_HOST: str = "http://localhost:3030"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()