import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.future import select
from src.database import async_session_factory
from src.models import JobStatusEnum, PriceSnapshot, Product, ScrapeJob, StoreEnum
from src.scrapers.base import BaseOpticalScraper
from src.scrapers.gmo import GMOScraper
from src.scrapers.rotter_krauss import RotterKraussScraper
from src.scrapers.schilling import SchillingScraper
from src.scrapers.place_vendome import PlaceVendomeScraper
from src.scrapers.econopticas import EconopticasScraper
from src.scrapers.karun import KarunScraper
from src.scrapers.lentesplus import LentesplusScraper
from src.services.ollama import ollama_service

logger = logging.getLogger(__name__)

SCRAPER_REGISTRY: Dict[str, type[BaseOpticalScraper]] = {
    StoreEnum.GMO.value: GMOScraper,
    StoreEnum.ROTTER_KRAUSS.value: RotterKraussScraper,
    StoreEnum.SCHILLING.value: SchillingScraper,
    StoreEnum.PLACE_VENDOME.value: PlaceVendomeScraper,
    StoreEnum.ECONOPTICAS.value: EconopticasScraper,
    StoreEnum.KARUN.value: KarunScraper,
    StoreEnum.LENTESPLUS.value: LentesplusScraper,
}


def get_available_stores() -> List[str]:
    return list(SCRAPER_REGISTRY.keys())


async def execute_scrape_for_store(store: str, max_pages: Optional[int] = None) -> ScrapeJob:
    scraper_cls = SCRAPER_REGISTRY.get(store)
    if not scraper_cls:
        raise ValueError(f"Unknown store adapter: {store}")

    scraper = scraper_cls()
    now = datetime.utcnow()

    async with async_session_factory() as session:
        job = ScrapeJob(store=store, status=JobStatusEnum.RUNNING.value, started_at=now)
        session.add(job)
        await session.commit()
        await session.refresh(job)

        items_scraped = 0
        items_updated = 0

        try:
            async for item in scraper.scrape_catalog(max_pages=max_pages):
                items_scraped += 1
                prod_uid = f"{item.store}:{item.store_product_id}"

                stmt = select(Product).where(Product.id == prod_uid)
                res = await session.execute(stmt)
                existing_prod = res.scalar_one_or_none()

                import re
                clean_desc = re.sub(r"<[^>]+>", " ", item.description or "")[:200]
                embed_text = f"{item.brand} {item.model_name} {item.category} {clean_desc}".strip()
                embedding = None
                try:
                    embedding = await ollama_service.get_embedding(embed_text)
                except Exception as emb_err:
                    logger.warning(f"Embedding generation failed for {prod_uid}: {emb_err}")

                if existing_prod:
                    existing_prod.brand = item.brand
                    existing_prod.model_name = item.model_name
                    existing_prod.category = item.category
                    existing_prod.url = item.url
                    existing_prod.image_url = item.image_url or existing_prod.image_url
                    if embedding:
                        existing_prod.embedding = embedding
                    existing_prod.updated_at = now
                    product_id = existing_prod.id
                    items_updated += 1
                else:
                    new_prod = Product(
                        id=prod_uid,
                        store=item.store,
                        store_product_id=item.store_product_id,
                        brand=item.brand,
                        model_name=item.model_name,
                        category=item.category,
                        url=item.url,
                        image_url=item.image_url,
                        description=item.description,
                        embedding=embedding,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(new_prod)
                    product_id = new_prod.id

                discount_pct = None
                if item.price_discount and item.price_normal > item.price_discount:
                    discount_pct = round(
                        ((item.price_normal - item.price_discount) / item.price_normal) * 100, 2
                    )

                today_start = datetime(now.year, now.month, now.day)
                stmt_snap = select(PriceSnapshot).where(
                    PriceSnapshot.product_id == product_id,
                    PriceSnapshot.scraped_at >= today_start
                ).order_by(PriceSnapshot.scraped_at.desc())
                res_snap = await session.execute(stmt_snap)
                today_snapshot = res_snap.scalars().first()

                if today_snapshot:
                    today_snapshot.price_normal = item.price_normal
                    today_snapshot.price_discount = item.price_discount
                    today_snapshot.discount_percentage = discount_pct
                    today_snapshot.is_in_stock = item.is_in_stock
                    today_snapshot.scraped_at = now
                else:
                    snapshot = PriceSnapshot(
                        product_id=product_id,
                        price_normal=item.price_normal,
                        price_discount=item.price_discount,
                        discount_percentage=discount_pct,
                        is_in_stock=item.is_in_stock,
                        scraped_at=now,
                    )
                    session.add(snapshot)

                if items_scraped % 50 == 0:
                    await session.commit()

            job.status = JobStatusEnum.COMPLETED.value
            job.items_scraped = items_scraped
            job.items_updated = items_updated
            job.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(job)
            logger.info(f"Scrape completed for {store}: {items_scraped} scraped, {items_updated} updated.")
            return job

        except Exception as e:
            logger.error(f"Scrape job failed for {store}: {e}", exc_info=True)
            job.status = JobStatusEnum.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(job)
            return job