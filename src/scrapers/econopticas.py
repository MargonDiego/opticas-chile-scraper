import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class EconopticasScraper(BaseOpticalScraper):
    """Scraper adapter for Econópticas (econopticas.cl - Magento 2)."""

    def __init__(self):
        super().__init__(store_name="econopticas", base_url="https://www.econopticas.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 50
        categories = [
            "/anteojos-opticos",
            "/anteojos-de-sol",
            "/lentes-de-contacto",
        ]

        async with await self.get_client() as client:
            for cat_path in categories:
                for page in range(1, limit_pages + 1):
                    url = f"{self.base_url}{cat_path}?p={page}"
                    res = await self.fetch_with_retry(client, "GET", url)
                    if res is None:
                        logger.error(f"Econopticas {url} unreachable after retries, stopping category {cat_path}")
                        break
                    if res.status_code != 200:
                        logger.warning(f"Econopticas {url} returned status {res.status_code}")
                        break

                    soup = BeautifulSoup(res.text, "lxml")
                    items = soup.select(".product-item-info, .product-item")
                    if not items:
                        if page == 1:
                            logger.error(f"Econopticas {cat_path} returned zero items on page 1 - possible selector break, not end of catalog")
                        break

                    page_has_items = False
                    for tile in items:
                        item = self._parse_tile(tile, cat_path)
                        if item:
                            page_has_items = True
                            yield item

                    if not page_has_items:
                        break

                    next_btn = soup.select_one(".action.next")
                    if not next_btn:
                        break

    def _parse_tile(self, tile, cat_path: str = "") -> Optional[ScrapedItem]:
        try:
            link_el = tile.select_one("a.product-item-photo, .product-link a, a[href*='.html']")
            if not link_el:
                return None

            href = link_el.get("href", "")
            if not href:
                return None
            if not href.startswith("http"):
                href = f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"

            title_el = tile.select_one(".product-link a, .product-item-name a, .product-brand")
            brand_el = tile.select_one(".product-brand a, .product-brand")

            name = title_el.text.strip() if title_el else ""
            brand = brand_el.text.strip() if brand_el else ""

            if not name:
                slug = href.split("/")[-1].replace(".html", "").replace("-", " ").title()
                name = f"Lentes {slug}"
            if not brand:
                brand = name.split()[0] if name else "Econopticas"

            # Image
            img_el = tile.select_one("img.product-image-photo, img")
            image_url = None
            if img_el:
                src = img_el.get("data-src") or img_el.get("src") or img_el.get("data-lazy-src")
                if src:
                    src = src.strip()
                    if src.startswith("//"):
                        image_url = f"https:{src}"
                    elif not src.startswith("http"):
                        image_url = f"{self.base_url.rstrip('/')}/{src.lstrip('/')}"
                    else:
                        image_url = src

            # Prices
            special_p = tile.select_one(".special-price .price")
            old_p = tile.select_one(".old-price .price")
            normal_p = tile.select_one(".price-box .price, .price-container .price, .price")

            price_discount = clean_clp_price(special_p.text) if special_p else None
            price_normal = (
                clean_clp_price(old_p.text)
                if old_p
                else (clean_clp_price(normal_p.text) if normal_p else None)
            )

            if price_discount and price_normal and price_discount >= price_normal:
                price_discount = None
            elif price_discount and not price_normal:
                price_normal = price_discount
                price_discount = None

            if not price_normal:
                return None

            prod_id = href.split("/")[-1].replace(".html", "")

            return ScrapedItem(
                store=self.store_name,
                store_product_id=prod_id,
                brand=brand,
                model_name=name,
                category=detect_category(f"{name} {brand}", cat_path),
                url=href,
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                is_in_stock=True,
            )
        except Exception as e:
            logger.debug(f"Error parsing Econopticas tile: {e}")
            return None