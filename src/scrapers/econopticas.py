import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class EconopticasScraper(BaseOpticalScraper):
    """Scraper adapter for Econópticas (econopticas.cl - GrandVision)."""

    def __init__(self):
        super().__init__(store_name="econopticas", base_url="https://www.econopticas.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 3
        categories = [
            "/lentes-de-contacto",
            "/lentes-de-contacto?prefn1=economic_visualCondition&prefv1=Miop%c3%ada%20e%20Hipermetrop%c3%ada",
            "/lentes-de-contacto?prefn1=economic_visualCondition&prefv1=Astigmatismo",
        ]

        async with await self.get_client() as client:
            for cat_path in categories[:limit_pages]:
                url = f"{self.base_url}{cat_path}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "lxml")
                        tiles = soup.select(".product-tile, .product, .grid-tile")
                        for tile in tiles:
                            item = self._parse_tile(tile)
                            if item:
                                yield item
                except Exception as e:
                    logger.error(f"Error scraping Econopticas {url}: {e}")

    def _parse_tile(self, tile) -> Optional[ScrapedItem]:
        try:
            link_el = tile.select_one("a[href*='.html']")
            price_el = tile.select_one(".price .sales .value, .sales .value, .price .sales, .price, .value")
            img_el = tile.select_one("img")

            if link_el and price_el:
                href = link_el.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                
                # Title from link text or href slug
                name = link_el.text.strip()
                if not name or len(name) < 3:
                    slug = href.split("/")[-1].replace(".html", "").replace("-", " ").title()
                    name = f"Lentes {slug}"

                # Normalize image URL
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

                if price and name:
                    return ScrapedItem(
                        store=self.store_name,
                        store_product_id=href.split("/")[-1].replace(".html", ""),
                        brand=name.split()[0] if name else "Econopticas",
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