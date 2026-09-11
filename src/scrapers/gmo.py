import logging
from typing import AsyncGenerator, Optional
import httpx
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
        async with await self.get_client() as client:
            for page in range(1, limit_pages + 1):
                url = f"{self.base_url}/products.json?limit=250&page={page}"
                res = await self.fetch_with_retry(client, "GET", url)
                if res is None:
                    logger.error(f"GMO page {page} unreachable after retries, stopping catalog scrape")
                    break
                if res.status_code != 200:
                    logger.warning(f"GMO products.json returned status {res.status_code}")
                    break
                try:
                    data = res.json()
                    products = data.get("products", [])
                except Exception as e:
                    logger.error(f"Error parsing GMO page {page} response: {e}")
                    break
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