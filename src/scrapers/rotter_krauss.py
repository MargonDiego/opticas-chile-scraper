import logging
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class RotterKraussScraper(BaseOpticalScraper):
    """Scraper adapter for Rotter & Krauss (ryk.cl)."""

    def __init__(self):
        super().__init__(store_name="ryk", base_url="https://www.ryk.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 50
        page_size = 24
        categories = [
            "/anteojos-opticos",
            "/anteojos-de-sol",
            "/lentes-de-contacto",
        ]

        async with await self.get_client() as client:
            for cat_path in categories:
                for page in range(0, limit_pages):
                    start = page * page_size
                    sep = "&" if "?" in cat_path else "?"
                    url = f"{self.base_url}{cat_path}{sep}sz={page_size}&start={start}"
                    try:
                        res = await client.get(url)
                        if res.status_code != 200:
                            break

                        soup = BeautifulSoup(res.text, "lxml")
                        # Pick top-level product containers with data-pid to avoid duplicates
                        cards = soup.select(".product[data-pid]")
                        if not cards:
                            cards = soup.select(".product-tile")
                        if not cards:
                            break

                        page_has_items = False
                        for card in cards:
                            item = self._parse_tile(card, cat_path)
                            if item:
                                page_has_items = True
                                yield item

                        if not page_has_items or len(cards) < page_size:
                            break

                    except Exception as e:
                        logger.error(f"Error scraping RyK {url}: {e}")
                        break

    def _parse_tile(self, card, cat_path: str = "") -> Optional[ScrapedItem]:
        try:
            # 1. Product Link and ID
            link_el = card.select_one(".pdp-link a, .product-tile a, a[href*='.html']")
            if not link_el:
                link_el = card.select_one("a[href]")
            if not link_el:
                return None

            href = link_el.get("href", "")
            if not href:
                return None
            if not href.startswith("http"):
                href = f"{self.base_url}{href}"

            store_product_id = card.get("data-pid")
            if not store_product_id:
                store_product_id = href.split("/")[-1].replace(".html", "").split("?")[0]

            # 2. Product Name / Model Name
            # Prefer alt/title from tile-image or pdp-link text
            name = None
            img_el = card.select_one("img.tile-image, img.primary, img[src]")
            if img_el:
                name = img_el.get("title") or img_el.get("alt")

            if not name:
                pdp_el = card.select_one(".pdp-link a, .product-name a, .pdp-link, .product-name")
                if pdp_el:
                    name = pdp_el.text.strip()

            if not name:
                return None

            name = name.strip()

            # 3. Prices (Normal and Discount)
            list_price_el = card.select_one(".price .strike-through, .strike-through")
            sales_price_el = card.select_one(".price .sales, .sales")

            price_normal = None
            price_discount = None

            if list_price_el and sales_price_el:
                p_list = clean_clp_price(list_price_el.text)
                p_sales = clean_clp_price(sales_price_el.text)
                if p_list and p_sales and p_list > p_sales:
                    price_normal = p_list
                    price_discount = p_sales
                elif p_sales:
                    price_normal = p_sales
                elif p_list:
                    price_normal = p_list
            elif sales_price_el:
                price_normal = clean_clp_price(sales_price_el.text)
            else:
                price_el = card.select_one(".price")
                if price_el:
                    price_normal = clean_clp_price(price_el.text)

            if not price_normal:
                return None

            # 4. Image URL
            image_url = None
            if img_el:
                src = (
                    img_el.get("src")
                    or img_el.get("data-src")
                    or img_el.get("data-lazy-src")
                    or img_el.get("data-original")
                )
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

            # 5. Brand detection
            brand = name.split()[0] if name else "Rotter & Krauss"
            name_lower = name.lower()
            if name_lower.startswith("ray ban") or name_lower.startswith("ray-ban"):
                brand = "Ray-Ban"
            elif name_lower.startswith("oakley"):
                brand = "Oakley"
            elif name_lower.startswith("vogue"):
                brand = "Vogue"
            elif name_lower.startswith("armani exchange"):
                brand = "Armani Exchange"
            elif name_lower.startswith("emporio armani"):
                brand = "Emporio Armani"
            elif name_lower.startswith("michael kors"):
                brand = "Michael Kors"
            elif name_lower.startswith("acuvue"):
                brand = "Acuvue"
            elif name_lower.startswith("alcon") or name_lower.startswith("dailies") or name_lower.startswith("air optix"):
                brand = "Alcon"
            elif name_lower.startswith("bausch + lomb") or name_lower.startswith("bausch & lomb") or name_lower.startswith("soflens") or name_lower.startswith("biotrue"):
                brand = "Bausch + Lomb"
            elif name_lower.startswith("coopervision") or name_lower.startswith("biofinity") or name_lower.startswith("clariti") or name_lower.startswith("proclear"):
                brand = "CooperVision"

            return ScrapedItem(
                store=self.store_name,
                store_product_id=store_product_id,
                brand=brand,
                model_name=name,
                category=detect_category(name, cat_path),
                url=href,
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                is_in_stock=True,
            )
        except Exception as e:
            logger.debug(f"Error parsing tile: {e}")
            return None