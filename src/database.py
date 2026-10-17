import os
import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from src.config import settings

logger = logging.getLogger(__name__)

if settings.DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Initialize tables and create pgvector extension if on PostgreSQL."""
    async with engine.begin() as conn:
        if settings.DATABASE_URL.startswith("postgresql"):
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("pgvector extension initialized on PostgreSQL.")
            except Exception as e:
                logger.warning(f"Could not enable vector extension: {e}")

        await conn.run_sync(SQLModel.metadata.create_all)

        # Composite index on price_snapshots (product_id, scraped_at DESC) for sub-5ms catalog queries
        try:
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_price_snapshots_product_scraped "
                    "ON price_snapshots (product_id, scraped_at DESC);"
                )
            )
            logger.info("Composite index ix_price_snapshots_product_scraped ensured.")
        except Exception as e:
            logger.warning(f"Could not create composite index: {e}")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()