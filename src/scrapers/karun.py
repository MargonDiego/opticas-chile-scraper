import logging
from typing import AsyncGenerator, Optional
import httpx
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class KarunScraper(BaseOpticalScraper):
    """Scraper adapter for Karün Chile (latam.karunworld.com / karun.cl)."""

    def __init__(self):
        super().__init__(store_name="karun", base_url="https://latam.karunworld.com")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 10
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
                        break
                except Exception as e:
                    logger.error(f"Error scraping Karun page {page}: {e}")
                    break

    def _parse_shopify(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            prod_id = str(prod.get("id"))
            title = prod.get("title", "")
            vendor = prod.get("vendor", "Karün")
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

            if not price_normal or price_normal <= 0:
                return None

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
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                description=prod.get("body_html"),
                is_in_stock=in_stock,
            )
        except Exception:
            return None