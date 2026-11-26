import logging
from typing import AsyncGenerator, Optional
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, detect_category

logger = logging.getLogger(__name__)


class PlaceVendomeScraper(BaseOpticalScraper):
    """Scraper adapter for Place Vendôme (opv.cl / placevendome.cl)."""

    def __init__(self):
        super().__init__(store_name="place_vendome", base_url="https://www.opv.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 50
        for page in range(1, limit_pages + 1):
            # Primary feed: Shopify products.json. VTEX search is the fallback
            # when the Shopify feed is unavailable.
            url = f"{self.base_url}/products.json?limit=250&page={page}"
            data = await self.fetch_json_impersonated(url)
            if data is not None:
                products = data.get("products", [])
                if not products:
                    if page == 1:
                        logger.error("Place Vendome Shopify feed returned zero products on page 1 - possible API/selector break")
                    break
                for prod in products:
                    item = self._parse_shopify(prod)
                    if item:
                        yield item
                continue

            vtex_url = f"{self.base_url}/api/catalog_system/pub/products/search?_from={(page-1)*50}&_to={page*50-1}"
            vtex_items = await self.fetch_json_impersonated(vtex_url)
            if vtex_items is None:
                logger.error(f"Place Vendome VTEX fallback page {page} unreachable after retries, stopping catalog scrape")
                break
            if not vtex_items:
                if page == 1:
                    logger.error("Place Vendome VTEX feed returned zero products on page 1 - possible API/selector break")
                break
            for prod in vtex_items:
                item = self._parse_vtex(prod)
                if item:
                    yield item

    def _parse_shopify(self, prod: dict) -> Optional[ScrapedItem]:
        return self.parse_shopify_product(prod, default_vendor="Place Vendome")

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
