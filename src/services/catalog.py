import time
from typing import List

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import noload, selectinload

from src.models import CatalogStatsRead, PriceSnapshot, Product, ProductRead
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

    # Only the latest snapshot per product is needed here, but
    # Product.price_snapshots defaults to eager-loading (lazy=selectin), so a
    # plain select(Product) would pull every historical row for all ~10k
    # products just to keep the newest one. Rank snapshots per product with a
    # window function and join in only rank #1, instead.
    latest_rank = (
        select(
            PriceSnapshot.product_id,
            PriceSnapshot.price_normal,
            PriceSnapshot.price_discount,
            PriceSnapshot.is_in_stock,
            func.row_number()
            .over(partition_by=PriceSnapshot.product_id, order_by=PriceSnapshot.scraped_at.desc())
            .label("rn"),
        )
    ).subquery()
    latest_snap = select(latest_rank).where(latest_rank.c.rn == 1).subquery()

    stmt = (
        select(
            Product,
            latest_snap.c.price_normal,
            latest_snap.c.price_discount,
            latest_snap.c.is_in_stock,
        )
        .outerjoin(latest_snap, Product.id == latest_snap.c.product_id)
        .options(noload(Product.price_snapshots))
    )
    prod_res = await session.execute(stmt)
    rows = prod_res.all()

    mapped_list: List[ProductRead] = []
    by_store = {}
    by_category = {}
    total_deals = 0
    total_in_stock = 0
    discount_sum = 0.0

    for prod, latest_price_normal, latest_price_discount, latest_is_in_stock in rows:
        by_store[prod.store] = by_store.get(prod.store, 0) + 1
        by_category[prod.category] = by_category.get(prod.category, 0) + 1

        mapped = ProductRead(
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
            current_price_normal=latest_price_normal,
            current_price_discount=latest_price_discount,
            current_in_stock=latest_is_in_stock,
        )
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
