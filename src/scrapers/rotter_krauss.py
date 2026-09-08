import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class RotterKraussScraper(BaseOpticalScraper):
    """Scraper adapter for Rotter & Krauss (ryk.cl / rotterandkrauss.cl)."""

    def __init__(self):
        super().__init__(store_name="ryk", base_url="https://www.rotterandkrauss.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 5
        async with await self.get_client() as client:
            # 1. Attempt Shopify products.json or VTEX catalog API
            for page in range(1, limit_pages + 1):
                # Try Shopify endpoint
                shopify_url = f"{self.base_url}/products.json?limit=50&page={page}"
                try:
                    res = await client.get(shopify_url)
                    if res.status_code == 200:
                        data = res.json()
                        products = data.get("products", [])
                        if not products:
                            break
                        for prod in products:
                            item = self._parse_shopify_product(prod)
                            if item:
                                yield item
                    else:
                        # Try VTEX endpoint
                        vtex_url = f"{self.base_url}/api/catalog_system/pub/products/search?_from={(page-1)*50}&_to={page*50-1}"
                        vtex_res = await client.get(vtex_url)
                        if vtex_res.status_code == 200:
                            vtex_prods = vtex_res.json()
                            if not vtex_prods:
                                break
                            for prod in vtex_prods:
                                item = self._parse_vtex_product(prod)
                                if item:
                                    yield item
                        else:
                            # HTML Fallback
                            async for item in self._scrape_html_fallback(client, page):
                                yield item
                except Exception as e:
                    logger.error(f"Error scraping Rotter & Krauss page {page}: {e}")
                    break

    def _parse_shopify_product(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            prod_id = str(prod.get("id"))
            title = prod.get("title", "")
            vendor = prod.get("vendor", "Rotter & Krauss")
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
            logger.debug(f"Error parsing R&K Shopify item: {e}")
            return None

    def _parse_vtex_product(self, prod: dict) -> Optional[ScrapedItem]:
        try:
            product_id = str(prod.get("productId", ""))
            name = prod.get("productName", "")
            brand = prod.get("brand", "Rotter & Krauss")
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
        except Exception as e:
            return None

    async def _scrape_html_fallback(
        self, client: httpx.AsyncClient, page: int
    ) -> AsyncGenerator[ScrapedItem, None]:
        url = f"{self.base_url}/collections/all?page={page}"
        res = await client.get(url)
        if res.status_code != 200:
            return
        soup = BeautifulSoup(res.text, "lxml")
        cards = soup.select(".grid-product, .product-item, .card")
        for card in cards:
            title_el = card.select_one(".grid-product__title, .product-title, h3")
            price_el = card.select_one(".grid-product__price, .price")
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
                        brand=name.split()[0] if name else "Rotter & Krauss",
                        model_name=name,
                        category=detect_category(name),
                        url=href,
                        price_normal=price,
                        is_in_stock=True,
                    )
