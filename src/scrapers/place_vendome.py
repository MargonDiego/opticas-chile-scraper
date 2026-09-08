import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class PlaceVendomeScraper(BaseOpticalScraper):
    """Scraper adapter for Place Vendôme (opv.cl / placevendome.cl)."""

    def __init__(self):
        super().__init__(store_name="place_vendome", base_url="https://www.opv.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 5
        async with await self.get_client() as client:
            for page in range(1, limit_pages + 1):
                # Try Shopify products.json
                url = f"{self.base_url}/products.json?limit=50&page={page}"
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
                        # Fallback VTEX search
                        vtex_url = f"{self.base_url}/api/catalog_system/pub/products/search?_from={(page-1)*50}&_to={page*50-1}"
                        vtex_res = await client.get(vtex_url)
                        if vtex_res.status_code == 200:
                            for prod in vtex_res.json():
                                item = self._parse_vtex(prod)
                                if item:
                                    yield item
                except Exception as e:
                    logger.error(f"Error scraping Place Vendome page {page}: {e}")
                    break

    def _parse_shopify(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            prod_id = str(prod.get("id"))
            title = prod.get("title", "")
            vendor = prod.get("vendor", "Place Vendome")
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
                is_in_stock=in_stock,
            )
        except Exception as e:
            return None

    def _parse_vtex(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            product_id = str(prod.get("productId", ""))
            name = prod.get("productName", "")
            brand = prod.get("brand", "Place Vendome")
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
