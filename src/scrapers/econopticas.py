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
        limit_pages = max_pages or 5
        async with await self.get_client() as client:
            for page in range(1, limit_pages + 1):
                url = f"{self.base_url}/api/catalog_system/pub/products/search?_from={(page-1)*50}&_to={page*50-1}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        products = res.json()
                        if not products:
                            break
                        for prod in products:
                            item = self._parse_vtex(prod)
                            if item:
                                yield item
                    else:
                        # Fallback to HTML
                        async for item in self._scrape_html(client, page):
                            yield item
                except Exception as e:
                    logger.error(f"Error scraping Econopticas page {page}: {e}")
                    break

    def _parse_vtex(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            product_id = str(prod.get("productId", ""))
            name = prod.get("productName", "")
            brand = prod.get("brand", "Econopticas")
            link = prod.get("link", "")
            if not link.startswith("http"):
                link = f"{self.base_url}{link}"

            items = prod.get("items", [])
            if not items:
                return None
            first_item = items[0]
            sellers = first_item.get("sellers", [])
            comm_offer = sellers[0].get("commertialOffer", {}) if sellers else {}

            price_normal = int(comm_offer.get("ListPrice", 0) or comm_offer.get("Price", 0))
            price_discount = int(comm_offer.get("Price", 0))
            if price_discount == price_normal:
                price_discount = None
            if price_normal == 0 and price_discount:
                price_normal = price_discount
                price_discount = None

            images = first_item.get("images", [])
            image_url = images[0].get("imageUrl") if images else None
            in_stock = comm_offer.get("AvailableQuantity", 0) > 0

            return ScrapedItem(
                store=self.store_name,
                store_product_id=product_id,
                brand=brand,
                model_name=name,
                category=detect_category(name),
                url=link,
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                is_in_stock=in_stock,
            )
        except Exception:
            return None

    async def _scrape_html(
        self, client: httpx.AsyncClient, page: int
    ) -> AsyncGenerator[ScrapedItem, None]:
        url = f"{self.base_url}/lentes-de-sol?page={page}"
        res = await client.get(url)
        if res.status_code != 200:
            return
        soup = BeautifulSoup(res.text, "lxml")
        cards = soup.select(".vtex-product-summary-2-x-container, .product-item")
        for card in cards:
            title_el = card.select_one(".vtex-product-summary-2-x-productBrand, h3")
            price_el = card.select_one(".vtex-product-price-1-x-currencyInteger, .price")
            link_el = card.select_one("a[href]")
            if title_el and price_el and link_el:
                name = title_el.text.strip()
                price = clean_clp_price(price_el.text)
                href = link_el.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                if price:
                    yield ScrapedItem(
                        store=self.store_name,
                        store_product_id=href.split("/")[-1],
                        brand=name.split()[0] if name else "Econopticas",
                        model_name=name,
                        category=detect_category(name),
                        url=href,
                        price_normal=price,
                        is_in_stock=True,
                    )
