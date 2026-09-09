import logging
from typing import AsyncGenerator, Optional
import httpx
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

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
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        products = data.get("products", [])
                        if not products:
                            break
                        for prod in products:
                            item = self._parse_shopify(prod)
                            if item:
                                yield item
                    else:
                        logger.warning(f"GMO products.json returned status {res.status_code}")
                        break
                except Exception as e:
                    logger.error(f"Error scraping GMO page {page}: {e}")
                    break

    def _parse_shopify(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            prod_id = str(prod.get("id"))
            title = prod.get("title", "")
            vendor = prod.get("vendor", "GMO")
            handle = prod.get("handle", "")
            url = f"{self.base_url}/products/{handle}"

            variants = prod.get("variants", [])
            if not variants:
                return None
            first_var = variants[0]
            price = clean_clp_price(first_var.get("price"))
            compare_price = clean_clp_price(first_var.get("compare_at_price"))

            price_normal = compare_price if compare_price and compare_price > price else price
            price_discount = price if compare_price and compare_price > price else None

            images = prod.get("images", [])
            image_url = images[0].get("src") if images else None
            in_stock = first_var.get("available", True)

            return ScrapedItem(
                store=self.store_name,
                store_product_id=prod_id,
                brand=vendor,
                model_name=title,
                category=detect_category(title + " " + prod.get("product_type", "")),
                url=url,
                price_normal=price_normal or 0,
                price_discount=price_discount,
                image_url=image_url,
                description=prod.get("body_html"),
                is_in_stock=in_stock,
            )
        except Exception as e:
            logger.debug(f"Error parsing GMO item: {e}")
            return None