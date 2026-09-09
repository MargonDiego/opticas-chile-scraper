import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class RotterKraussScraper(BaseOpticalScraper):
    """Scraper adapter for Rotter & Krauss (ryk.cl)."""

    def __init__(self):
        super().__init__(store_name="ryk", base_url="https://www.ryk.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 15
        page_size = 48
        categories = [
            "/anteojos-de-sol",
            "/lentes-de-contacto",
            "/anteojos-de-lujo.html",
        ]

        async with await self.get_client() as client:
            for cat_path in categories:
                for page in range(0, limit_pages):
                    start = page * page_size
                    sep = "&" if "?" in cat_path else "?"
                    url = f"{self.base_url}{cat_path}{sep}sz={page_size}&start={start}"
                    try:
                        res = await client.get(url)
                        if res.status_code != 200:
                            break

                        soup = BeautifulSoup(res.text, "lxml")
                        cards = soup.select(".product, .product-tile, .product-item, .tile")
                        if not cards:
                            break

                        page_has_items = False
                        for card in cards:
                            item = self._parse_tile(card)
                            if item:
                                page_has_items = True
                                yield item

                        if not page_has_items:
                            break

                    except Exception as e:
                        logger.error(f"Error scraping RyK {url}: {e}")
                        break

    def _parse_tile(self, card) -> Optional[ScrapedItem]:
        try:
            name_el = card.select_one(".pdp-link, .product-name, h2, h3, a")
            price_el = card.select_one(".price, .sales, .value")
            link_el = card.select_one("a[href]")
            img_el = card.select_one("img[src]")

            if name_el and price_el and link_el:
                name = name_el.text.strip()
                price = clean_clp_price(price_el.text)
                href = link_el.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                # Extract and normalize full image URL
                image_url = None
                if img_el:
                    src = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src") or img_el.get("data-original")
                    if not src and img_el.get("srcset"):
                        src = img_el.get("srcset").split(",")[0].split()[0]
                    if src:
                        src = src.strip()
                        if src.startswith("//"):
                            image_url = f"https:{src}"
                        elif not src.startswith("http"):
                            image_url = f"{self.base_url.rstrip('/')}/{src.lstrip('/')}"
                        else:
                            image_url = src

                if price:
                    return ScrapedItem(
                        store=self.store_name,
                        store_product_id=href.split("/")[-1].split("?")[0],
                        brand=name.split()[0] if name else "Rotter & Krauss",
                        model_name=name,
                        category=detect_category(name),
                        url=href,
                        price_normal=price,
                        image_url=image_url,
                        is_in_stock=True,
                    )
        except Exception:
            return None
        return None