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

pool_kwargs = {}
if not settings.DATABASE_URL.startswith("sqlite"):
    pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    **pool_kwargs,
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

        # Ensure current_price_normal, current_price_discount, current_in_stock columns exist and backfill
        try:
            if settings.DATABASE_URL.startswith("postgresql"):
                await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS current_price_normal INTEGER;"))
                await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS current_price_discount INTEGER;"))
                await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS current_in_stock BOOLEAN DEFAULT TRUE;"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_current_price_normal ON products (current_price_normal);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_current_price_discount ON products (current_price_discount);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_current_in_stock ON products (current_in_stock);"))

                # Backfill from latest snapshot for existing rows
                await conn.execute(text("""
                    UPDATE products p
                    SET current_price_normal = s.price_normal,
                        current_price_discount = s.price_discount,
                        current_in_stock = s.is_in_stock
                    FROM (
                        SELECT DISTINCT ON (product_id) product_id, price_normal, price_discount, is_in_stock
                        FROM price_snapshots
                        ORDER BY product_id, scraped_at DESC
                    ) s
                    WHERE p.id = s.product_id
                      AND p.current_price_normal IS NULL;
                """))
                logger.info("PostgreSQL products current price migration and backfill completed.")
            else:
                # SQLite schema check and backfill
                pragma_res = await conn.execute(text("PRAGMA table_info(products);"))
                cols = {row[1] for row in pragma_res.fetchall()}
                if "current_price_normal" not in cols:
                    await conn.execute(text("ALTER TABLE products ADD COLUMN current_price_normal INTEGER;"))
                if "current_price_discount" not in cols:
                    await conn.execute(text("ALTER TABLE products ADD COLUMN current_price_discount INTEGER;"))
                if "current_in_stock" not in cols:
                    await conn.execute(text("ALTER TABLE products ADD COLUMN current_in_stock BOOLEAN DEFAULT 1;"))

                await conn.execute(text("""
                    UPDATE products
                    SET current_price_normal = (
                        SELECT s.price_normal FROM price_snapshots s
                        WHERE s.product_id = products.id
                        ORDER BY s.scraped_at DESC LIMIT 1
                    ),
                    current_price_discount = (
                        SELECT s.price_discount FROM price_snapshots s
                        WHERE s.product_id = products.id
                        ORDER BY s.scraped_at DESC LIMIT 1
                    ),
                    current_in_stock = (
                        SELECT s.is_in_stock FROM price_snapshots s
                        WHERE s.product_id = products.id
                        ORDER BY s.scraped_at DESC LIMIT 1
                    )
                    WHERE current_price_normal IS NULL
                      AND EXISTS (SELECT 1 FROM price_snapshots WHERE product_id = products.id);
                """))
                logger.info("SQLite products current price migration and backfill completed.")
        except Exception as e:
            logger.warning(f"Could not apply current_price columns migration/backfill: {e}")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()