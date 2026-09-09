import json
import logging
import re
from typing import AsyncGenerator, Optional
import httpx
from bs4 import BeautifulSoup
from src.scrapers.base import BaseOpticalScraper, ScrapedItem, clean_clp_price, detect_category

logger = logging.getLogger(__name__)


class SchillingScraper(BaseOpticalScraper):
    """Scraper adapter for Ópticas Schilling (schilling.cl - Magento 2)."""

    def __init__(self):
        super().__init__(store_name="schilling", base_url="https://www.schilling.cl")

    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        limit_pages = max_pages or 30
        categories = [
            "/lentes-opticos.html",
            "/lentes-de-sol.html",
            "/lentes-de-contacto.html",
            "/lentes-de-lectura.html",
            "/lentes-filtro-azul.html",
        ]

        async with await self.get_client() as client:
            for cat in categories:
                for page in range(1, limit_pages + 1):
                    url = f"{self.base_url}{cat}?p={page}"
                    try:
                        res = await client.get(url)
                        if res.status_code != 200:
                            break

                        soup = BeautifulSoup(res.text, "lxml")
                        cards = soup.select(".product-item-info")
                        if not cards:
                            break

                        page_has_items = False
                        for card in cards:
                            item = self._parse_card(card, cat)
                            if item:
                                page_has_items = True
                                yield item

                        if not page_has_items:
                            break

                        # Stop if no "next" page button in toolbar
                        next_btn = soup.select_one(".action.next")
                        if not next_btn:
                            break

                    except Exception as e:
                        logger.error(f"Error scraping Schilling {url}: {e}")
                        break

    def _parse_card(self, card, cat_path: str = "") -> Optional[ScrapedItem]:
        try:
            # 1. Product Link
            link_el = card.select_one("a.product-item-photo, a[href*='.html']")
            if not link_el:
                return None
            href = link_el.get("href", "")
            if not href:
                return None
            if not href.startswith("http"):
                href = f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"

            # 2. Product Name
            name_el = card.select_one(".product-item-name, a.product-item-link, strong")
            name = name_el.text.strip() if name_el else ""
            if not name:
                img_el = card.select_one("img.product-image-photo, img")
                if img_el:
                    name = img_el.get("alt") or img_el.get("title") or ""
            if not name or len(name) < 3 or name.endswith("%"):
                return None

            # 3. Brand extraction from GA4 onclick JSON or name parsing
            brand = "Schilling"
            onclick = link_el.get("onclick", "")
            if "item_brand" in onclick:
                m = re.search(r'["\']item_brand["\']\s*:\s*["\']([^"\']+)["\']', onclick)
                if m:
                    b_candidate = m.group(1).encode().decode("unicode_escape", errors="ignore")
                    if b_candidate and len(b_candidate) > 1:
                        brand = b_candidate

            if brand == "Schilling":
                # Heuristic cleanup from name
                clean_name = re.sub(r"^(Lentes\s+Ópticos|Lentes\s+de\s+Sol|Marco\s+para\s+Lentes\s+Ópticos|Lentes\s+de\s+Contacto|Lentes\s+Filtro\s+Azul|Lentes\s+de\s+Lectura)\s+", "", name, flags=re.IGNORECASE)
                parts = clean_name.split()
                if parts:
                    brand = parts[0]

            # 4. Prices (Normal and Discount)
            special_p = card.select_one(".special-price .price")
            old_p = card.select_one(".old-price .price")
            reg_p = card.select_one(".price-box .price, .price-wrapper .price, .price")

            price_normal = None
            price_discount = None

            if special_p and old_p:
                p_disc = clean_clp_price(special_p.text)
                p_norm = clean_clp_price(old_p.text)
                if p_norm and p_disc and p_norm > p_disc:
                    price_normal = p_norm
                    price_discount = p_disc
                elif p_norm:
                    price_normal = p_norm
                elif p_disc:
                    price_normal = p_disc
            elif reg_p:
                price_normal = clean_clp_price(reg_p.text)

            if not price_normal:
                return None

            # 5. Image
            img_el = card.select_one("img.product-image-photo, img")
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

            prod_id = href.split("/")[-1].replace(".html", "")

            return ScrapedItem(
                store=self.store_name,
                store_product_id=prod_id,
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
            logger.debug(f"Error parsing Schilling card: {e}")
            return None