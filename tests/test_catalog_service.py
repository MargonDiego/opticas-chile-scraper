from datetime import datetime, timedelta

import pytest
from src.database import async_session_factory
from src.models import Product, PriceSnapshot
from src.services import catalog as catalog_service
from src.services.catalog import get_cached_catalog


@pytest.mark.asyncio
async def test_get_cached_catalog_uses_latest_snapshot_per_product():
    # The catalog cache is module-level and outlives the per-test DB reset,
    # so force a fresh query instead of reading another test's cached result.
    catalog_service._CATALOG_CACHE["products"] = []
    catalog_service._CATALOG_CACHE["timestamp"] = 0.0

    async with async_session_factory() as session:
        product = Product(
            id="gmo:test-latest-snapshot",
            store="gmo",
            store_product_id="test-latest-snapshot",
            brand="Ray-Ban",
            model_name="Aviator Test",
            category="sol",
            url="https://gmo.cl/ray-ban-aviator-test",
        )
        session.add(product)

        base_time = datetime.utcnow() - timedelta(days=5)
        snapshots = [
            PriceSnapshot(
                product_id=product.id,
                price_normal=100000,
                price_discount=None,
                is_in_stock=True,
                scraped_at=base_time + timedelta(days=i),
            )
            for i in range(4)
        ]
        # The most recent snapshot is the one with a discount - this is what
        # should win, not an arbitrary/first row.
        snapshots.append(
            PriceSnapshot(
                product_id=product.id,
                price_normal=100000,
                price_discount=59000,
                is_in_stock=True,
                scraped_at=base_time + timedelta(days=10),
            )
        )
        for s in snapshots:
            session.add(s)
        await session.commit()

        products, stats = await get_cached_catalog(session)

        match = next(p for p in products if p.id == product.id)
        assert match.current_price_normal == 100000
        assert match.current_price_discount == 59000
        assert stats.total_products == len(products)
