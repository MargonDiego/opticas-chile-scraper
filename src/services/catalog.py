import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models import CatalogStatsRead, Product, ProductRead
from src.scrapers.registry import get_available_stores

_CATALOG_CACHE = {
    "products": [],
    "stats": None,
    "timestamp": 0.0,
    "ttl_seconds": 180.0,  # 3 minutes cache
}


def map_product_read(prod: Product) -> ProductRead:
    latest = None
    if prod.price_snapshots:
        sorted_snaps = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)
        latest = sorted_snaps[0]

    return ProductRead(
        id=prod.id,
        store=prod.store,
        store_product_id=prod.store_product_id,
        brand=prod.brand,
        model_name=prod.model_name,
        category=prod.category,
        url=prod.url,
        image_url=prod.image_url,
        description=prod.description,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        current_price_normal=latest.price_normal if latest else None,
        current_price_discount=latest.price_discount if latest else None,
        current_in_stock=latest.is_in_stock if latest else None,
    )


async def get_cached_catalog(session: AsyncSession) -> tuple[List[ProductRead], CatalogStatsRead]:
    """Return the full mapped catalog and aggregated stats, memoized for ttl_seconds."""
    now = time.time()
    if _CATALOG_CACHE["products"] and (now - _CATALOG_CACHE["timestamp"]) < _CATALOG_CACHE["ttl_seconds"]:
        return _CATALOG_CACHE["products"], _CATALOG_CACHE["stats"]

    prod_res = await session.execute(select(Product).options(selectinload(Product.price_snapshots)))
    products = prod_res.scalars().all()

    mapped_list: List[ProductRead] = []
    by_store = {}
    by_category = {}
    total_deals = 0
    total_in_stock = 0
    discount_sum = 0.0

    for prod in products:
        by_store[prod.store] = by_store.get(prod.store, 0) + 1
        by_category[prod.category] = by_category.get(prod.category, 0) + 1

        mapped = map_product_read(prod)
        mapped_list.append(mapped)

        if mapped.current_in_stock is not False:
            total_in_stock += 1
        if (
            mapped.current_price_discount
            and mapped.current_price_normal
            and mapped.current_price_discount < mapped.current_price_normal
        ):
            total_deals += 1
            pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
            discount_sum += pct

    avg_discount = int(round(discount_sum / total_deals)) if total_deals > 0 else 0

    stats = CatalogStatsRead(
        total_products=len(mapped_list),
        total_deals=total_deals,
        avg_discount_percentage=avg_discount,
        total_stores=len(by_store) if by_store else len(get_available_stores()),
        total_in_stock=total_in_stock,
        by_store=by_store,
        by_category=by_category,
    )

    _CATALOG_CACHE["products"] = mapped_list
    _CATALOG_CACHE["stats"] = stats
    _CATALOG_CACHE["timestamp"] = now

    return mapped_list, stats
