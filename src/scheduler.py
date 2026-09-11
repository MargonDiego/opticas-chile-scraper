import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.config import settings
from src.scrapers.registry import get_available_stores, execute_scrape_for_store

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_scrape_all_stores():
    """Background cron job to scrape all optical chains periodically."""
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
