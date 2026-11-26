import asyncio
import hashlib
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from src.config import settings
from src.database import engine
from src.scrapers.registry import get_available_stores, execute_scrape_for_store

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Stable advisory-lock key (any int32) shared by every uvicorn worker.
_SCRAPE_LOCK_KEY = 0x5C4A9E01
# A lock older than this is considered abandoned (crashed worker) and stolen.
_SCRAPE_LOCK_STALE_SECONDS = 6 * 60 * 60

# File-based lock for non-Postgres backends; scoped per database URL so
# separate environments on the same host do not block each other.
SCRAPE_LOCK_FILE = Path(tempfile.gettempdir()) / (
    "opticas-scrape-" + hashlib.sha1(settings.DATABASE_URL.encode()).hexdigest()[:12] + ".lock"
)


def _try_file_lock() -> bool:
    """Atomically create the lock file. Returns False if another process holds it."""
    for _ in range(2):
        try:
            fd = os.open(SCRAPE_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - SCRAPE_LOCK_FILE.stat().st_mtime
            except FileNotFoundError:
                continue  # released between the open and the stat; retry
            if age <= _SCRAPE_LOCK_STALE_SECONDS:
                return False
            try:
                SCRAPE_LOCK_FILE.unlink()
            except FileNotFoundError:
                pass
            continue
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
        return True
    return False


def _release_file_lock() -> None:
    try:
        SCRAPE_LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


@asynccontextmanager
async def scheduled_scrape_lock():
    """Yield True when this worker won the cross-process scheduled-scrape lock.

    uvicorn runs with --workers 2, so every cron tick fires once per worker.
    Postgres uses a session-level advisory lock; other backends (SQLite) use
    an exclusive lock file. Losers yield False and must skip the scrape.
    """
    if settings.DATABASE_URL.startswith("postgresql"):
        async with engine.connect() as conn:
            acquired = bool(
                (
                    await conn.execute(
                        text("SELECT pg_try_advisory_lock(:key)"), {"key": _SCRAPE_LOCK_KEY}
                    )
                ).scalar()
            )
            try:
                yield acquired
            finally:
                if acquired:
                    await conn.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": _SCRAPE_LOCK_KEY}
                    )
    else:
        acquired = _try_file_lock()
        try:
            yield acquired
        finally:
            if acquired:
                _release_file_lock()


async def scheduled_scrape_all_stores():
    """Background cron job to scrape all optical chains periodically."""
    async with scheduled_scrape_lock() as acquired:
        if not acquired:
            logger.info("Scheduled scrape skipped: another worker holds the scrape lock.")
            return

        logger.info("Starting scheduled scrape for all Chilean optical stores...")
        stores = get_available_stores()
        for store in stores:
            try:
                logger.info(f"Running scheduled scrape for: {store}")
                await execute_scrape_for_store(store, max_pages=None)
            except Exception as e:
                logger.error(f"Scheduled scrape failed for store {store}: {e}")


def start_scheduler():
    """Start APScheduler background scheduler with fixed cron triggers (04:00 and 16:00)."""
    trigger = CronTrigger(hour="4,16", minute="0")
    scheduler.add_job(
        scheduled_scrape_all_stores,
        trigger=trigger,
        id="scrape_all_optical_stores",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scraper scheduler started with fixed daily cron schedule at 04:00 and 16:00.")


def shutdown_scheduler():
    """Graceful shutdown for scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scraper scheduler shut down.")
