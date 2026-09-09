import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class LentesplusScraper(BaseOpticalScraper):
    """Scraper adapter for Lentesplus Chile (lentesplus.com/cl - GraphQL API)."""

    def __init__(self):
        super().__init__(store_name="lentesplus", base_url="https://www.lentesplus.com")
        self.graphql_url = "https://www.lentesplus.com/graphql"

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 10
        page_size = 100

        query = """
        query GetCatalogProducts($pageSize: Int!, $currentPage: Int!) {
          products(search: "", pageSize: $pageSize, currentPage: $currentPage) {
            total_count
            items {
              id
              sku
              name
              url_key
              url_suffix
              stock_status
              image {
                url
                label
              }
              price_range {
                minimum_price {
                  regular_price {
                    value
                    currency
                  }
                  final_price {
                    value
                    currency
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
            }
          }
        }
        """

        headers = {
            "Content-Type": "application/json",
            "Store": "cl",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(headers=headers, timeout=25.0) as client:
            for page in range(1, limit_pages + 1):
                try:
                    payload = {
                        "query": query,
                        "variables": {
                            "pageSize": page_size,
                            "currentPage": page,
                        },
                    }
                    res = await client.post(self.graphql_url, json=payload)
                    if res.status_code != 200:
                        logger.error(f"Lentesplus GraphQL returned status {res.status_code}")
                        break

                    data = res.json()
                    products_data = data.get("data", {}).get("products", {})
                    items = products_data.get("items", [])
                    if not items:
                        break

                    for p in items:
                        item = self._parse_graphql_item(p)
                        if item:
                            yield item

                except Exception as e:
                    logger.error(f"Error scraping Lentesplus page {page}: {e}")
                    break

    def _parse_graphql_item(self, p: dict) -> Optional[ScrapedItem]:
        try:
            name = p.get("name", "").strip()
            if not name:
                return None

            sku = str(p.get("sku") or p.get("id"))
            url_key = p.get("url_key", "")
            suffix = p.get("url_suffix") or ".html"
            url = f"https://www.lentesplus.com/cl/{url_key}{suffix}" if url_key else f"https://www.lentesplus.com/cl/{sku}"

            price_range = p.get("price_range", {}).get("minimum_price", {})
            reg_price_obj = price_range.get("regular_price", {})
            fin_price_obj = price_range.get("final_price", {})

            price_normal = clean_clp_price(reg_price_obj.get("value"))
            price_discount = clean_clp_price(fin_price_obj.get("value"))

            if price_discount and price_normal and price_discount >= price_normal:
                price_discount = None
            elif price_discount and not price_normal:
                price_normal = price_discount
                price_discount = None

            if not price_normal:
                return None

            image_obj = p.get("image", {})
            image_url = image_obj.get("url") if image_obj else None

            is_in_stock = p.get("stock_status") == "IN_STOCK"

            # Brand detection
            brand = "Lentesplus"
            first_word = name.split()[0] if name else ""
            known_brands = ["Acuvue", "Biofinity", "Air Optix", "Soflens", "PureVision", "Biotrue", "Dailies", "Clariti", "Avaira", "Ultra", "Opti-Free", "Renu", "Biotrue"]
            for kb in known_brands:
                if kb.lower() in name.lower():
                    brand = kb
                    break

            return ScrapedItem(
                store=self.store_name,
                store_product_id=sku,
                brand=brand,
                model_name=name,
                category=detect_category(name),
                url=url,
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                is_in_stock=is_in_stock,
            )
        except Exception as e:
            logger.debug(f"Error parsing Lentesplus item: {e}")
            return None