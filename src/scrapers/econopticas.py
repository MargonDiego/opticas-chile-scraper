import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class EconopticasScraper(BaseOpticalScraper):
    """Scraper adapter for Econópticas (econopticas.cl)."""

    def __init__(self):
        super().__init__(store_name="econopticas", base_url="https://www.econopticas.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 3
        categories = ["/anteojos-de-sol", "/anteojos-opticos", "/lentes-de-contacto"]

        async with await self.get_client() as client:
            for cat in categories:
                for page in range(1, limit_pages + 1):
                    url = f"{self.base_url}{cat}?page={page}"
                    try:
                        res = await client.get(url)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, "lxml")
                            cards = soup.select(".vtex-product-summary-2-x-container, .product-card, article")
                            if not cards:
                                break
                            for card in cards:
                                item = self._parse_card(card)
                                if item:
                                    yield item
                    except Exception as e:
                        logger.error(f"Error scraping Econopticas {url}: {e}")
                        break

    def _parse_card(self, card) -> Optional[ScrapedItem]:
        try:
            title_el = card.select_one(".vtex-product-summary-2-x-productBrand, .product-name, h3, h2")
            price_el = card.select_one(".vtex-product-price-1-x-currencyInteger, .price, .selling-price")
            link_el = card.select_one("a[href]")
            img_el = card.select_one("img[src]")

            if title_el and price_el and link_el:
                name = title_el.text.strip()
                price = clean_clp_price(price_el.text)
                href = link_el.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                image_url = img_el.get("src") if img_el else None

                if price:
                    return ScrapedItem(
                        store=self.store_name,
                        store_product_id=href.split("/")[-1].split("?")[0],
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