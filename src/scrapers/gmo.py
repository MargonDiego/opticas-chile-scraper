import logging
from typing import AsyncGenerator, Optional
from src.scrapers.base import BaseOpticalScraper, ScrapedItem

logger = logging.getLogger(__name__)


class GMOScraper(BaseOpticalScraper):
    """Scraper adapter for GMO Chile (gmo.cl) using Shopify JSON catalog."""

    def __init__(self):
        super().__init__(store_name="gmo", base_url="https://gmo.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 50
        for page in range(1, limit_pages + 1):
            url = f"{self.base_url}/products.json?limit=250&page={page}"
            data = await self.fetch_json_impersonated(url)
            if data is None:
                logger.error(f"GMO page {page} unreachable after retries, stopping catalog scrape")
                break
            products = data.get("products", [])
            if not products:
                if page == 1:
                    logger.error("GMO returned zero products on page 1 - possible API/selector break, not end of catalog")
                break
            for prod in products:
                item = self._parse_shopify(prod)
                if item:
                    yield item

    def _parse_shopify(self, prod: dict) -> Optional[ScrapedItem]:
        return self.parse_shopify_product(prod, default_vendor="GMO")