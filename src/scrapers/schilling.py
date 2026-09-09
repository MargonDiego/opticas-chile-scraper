import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class SchillingScraper(BaseOpticalScraper):
    """Scraper adapter for Ópticas Schilling (schilling.cl)."""

    def __init__(self):
        super().__init__(store_name="schilling", base_url="https://www.schilling.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 3
        categories = [
            "/lentes-de-contacto.html",
            "/lentes-de-contacto/condicion-visual/miopia-e-hipermetropia.html",
            "/lentes-de-contacto/condicion-visual/astigmatismo.html",
        ]

        async with await self.get_client() as client:
            for cat in categories:
                url = f"{self.base_url}{cat}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "lxml")
                        cards = soup.select(".product-item-info, .product-item")
                        for card in cards:
                            link_el = card.select_one(".product-item-link, a")
                            price_el = card.select_one(".price, .price-box")
                            img_el = card.select_one("img")

                            if link_el and price_el:
                                name = link_el.text.strip()
                                price = clean_clp_price(price_el.text)
                                href = link_el.get("href", "")
                                image_url = img_el.get("src") if img_el else None

                                if price and name:
                                    yield ScrapedItem(
                                        store=self.store_name,
                                        store_product_id=href.split("/")[-1].replace(".html", ""),
                                        brand="Schilling",
                                        model_name=name,
                                        category=detect_category(name),
                                        url=href,
                                        price_normal=price,
                                        image_url=image_url,
                                        is_in_stock=True,
                                    )
                except Exception as e:
                    logger.error(f"Error scraping Schilling {url}: {e}")