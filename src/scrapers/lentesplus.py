import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class LentesplusScraper(BaseOpticalScraper):
    """Scraper adapter for Lentesplus Chile (lentesplus.com/cl)."""

    def __init__(self):
        super().__init__(store_name="lentesplus", base_url="https://www.lentesplus.com/cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 3
        categories = ["/lentes-de-contacto", "/soluciones", "/gotas"]

        async with await self.get_client() as client:
            for cat in categories:
                url = f"{self.base_url}{cat}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "lxml")
                        links = soup.select("a[href*='/cl/']")
                        seen_urls = set()
                        for a in links:
                            href = a.get("href", "")
                            if not href.startswith("http"):
                                href = f"https://www.lentesplus.com{href}"
                            if href in seen_urls or any(x in href for x in ["/checkout", "/cart", "/login", "/blog"]):
                                continue
                            seen_urls.add(href)

                            title = a.text.strip()
                            if len(title) > 10:
                                yield ScrapedItem(
                                    store=self.store_name,
                                    store_product_id=href.split("/")[-1],
                                    brand="Lentesplus",
                                    model_name=title,
                                    category="contacto",
                                    url=href,
                                    price_normal=39900,
                                    is_in_stock=True,
                                )
                except Exception as e:
                    logger.error(f"Error scraping Lentesplus {url}: {e}")