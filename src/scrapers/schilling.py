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
            for cat in categories[:limit_pages]:
                url = f"{self.base_url}{cat}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "lxml")
                        cards = soup.select(".product-item-info, .product-item")
                        for card in cards:
                            name_el = card.select_one(".product-item-name, a.product-item-link, strong")
                            price_el = card.select_one(".price-wrapper .price, .price-box .price, .price")
                            link_el = card.select_one("a[href*='.html']")
                            img_el = card.select_one("img")

                            if name_el and price_el and link_el:
                                name = name_el.text.strip()
                                # Clean price taking first number segment
                                price_lines = [l.strip() for l in price_el.text.split("\n") if l.strip()]
                                price = clean_clp_price(price_lines[0]) if price_lines else None
                                href = link_el.get("href", "")
                                image_url = None
                                if img_el:
                                    src = img_el.get("src") or img_el.get("data-src") or img_el.get("data-original")
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

                                if price and name and len(name) > 3 and not name.endswith("%"):
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