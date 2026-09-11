import abc
import asyncio
import logging
import re
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional
import httpx
from src.config import settings
from src.models import CategoryEnum

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    store: str
    store_product_id: str
    brand: str
    model_name: str
    category: str
    url: str
    price_normal: int
    price_discount: Optional[int] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_in_stock: bool = True


def clean_clp_price(raw_price: str | int | float | None) -> Optional[int]:
    """Normalize any CLP currency string or number to an integer in Chilean Pesos."""
    if raw_price is None:
        return None
    try:
        if isinstance(raw_price, (int, float)):
            val = int(raw_price)
        else:
            str_val = str(raw_price).strip()
            # If string ends with decimal cents like .00 or ,00 (common in APIs like Shopify)
            str_val = re.sub(r"[.,]\d{2}$", "", str_val)
            cleaned = re.sub(r"[^\d]", "", str_val)
            if not cleaned:
                return None
            val = int(cleaned)

        # Sanity check: optical products in CLP are typically 1,000 - 3,000,000 CLP.
        # Discard dummy/unrealistic values (like 98 billion CLP test prices)
        if val > 5000000 or val <= 0:
            return None
        return val
    except Exception:
        return None


def detect_category(text: str, fallback_text: str = "") -> str:
    """Heuristic categorization based on product titles or categories."""
    combined = f"{text} {fallback_text}".lower()
    if any(k in combined for k in ["sol", "sunglasses", "polarized", "polarizado"]):
        return CategoryEnum.SOL.value
    elif any(k in combined for k in ["contacto", "contact", "lentilla", "biofinity", "acuvue", "air optix", "soflens", "freeu", "precision 1", "dailies"]):
        return CategoryEnum.CONTACTO.value
    elif any(k in combined for k in ["óptico", "optico", "receta", "armazón", "armazon", "marcos", "cristal", "marco", "oftálmico", "oftalmico"]):
        return CategoryEnum.OPTICOS.value
    elif any(k in combined for k in ["estuche", "limpiador", "gotas", "solución", "solucion", "cordón", "paño"]):
        return CategoryEnum.ACCESORIOS.value
    return CategoryEnum.OTRO.value


# Known eyewear/contact-lens brands, keyed by the substring found in a raw
# product name/title. Shared across scrapers so each store doesn't repeat
# its own copy of the same brand table with slightly different matching.
KNOWN_EYEWEAR_BRANDS: dict[str, str] = {
    "ray-ban": "Ray-Ban",
    "ray ban": "Ray-Ban",
    "rayban": "Ray-Ban",
    "oakley": "Oakley",
    "vogue": "Vogue",
    "armani exchange": "Armani Exchange",
    "emporio armani": "Emporio Armani",
    "michael kors": "Michael Kors",
    "arnette": "Arnette",
    "carrera": "Carrera",
    "police": "Police",
    "hugo boss": "Boss",
    "boss": "Boss",
    "polo ralph lauren": "Polo Ralph Lauren",
    "ralph": "Ralph",
    "prada": "Prada",
    "versace": "Versace",
    "gucci": "Gucci",
    "burberry": "Burberry",
    "acuvue": "Acuvue",
    "biofinity": "CooperVision",
    "clariti": "CooperVision",
    "avaira": "CooperVision",
    "proclear": "CooperVision",
    "coopervision": "CooperVision",
    "air optix": "Alcon",
    "dailies": "Alcon",
    "opti-free": "Alcon",
    "alcon": "Alcon",
    "soflens": "Bausch + Lomb",
    "biotrue": "Bausch + Lomb",
    "purevision": "Bausch + Lomb",
    "renu": "Bausch + Lomb",
    "bausch + lomb": "Bausch + Lomb",
    "bausch & lomb": "Bausch + Lomb",
}


def detect_known_brand(name: str, default: str) -> str:
    """Match a raw product name against KNOWN_EYEWEAR_BRANDS, falling back
    to `default` (typically the store's own name or the name's first word)
    when nothing matches."""
    name_lower = name.lower()
    for needle, brand in KNOWN_EYEWEAR_BRANDS.items():
        if needle in name_lower:
            return brand
    return default


class BaseOpticalScraper(abc.ABC):
    """Abstract base scraper for Chilean optical store chains."""

    def __init__(self, store_name: str, base_url: str):
        self.store_name = store_name
        self.base_url = base_url
        self.headers = {
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            "Referer": self.base_url,
        }
        self.timeout = httpx.Timeout(settings.SCRAPER_TIMEOUT_SECONDS)

    async def get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=settings.SCRAPER_MAX_CONCURRENCY,
            ),
        )

    # Status codes worth retrying: rate limiting and transient upstream/server
    # failures. Other 4xx codes (404, 403, etc.) are treated as permanent -
    # retrying them would just waste requests against the target store.
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    async def fetch_with_retry(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs
    ) -> Optional[httpx.Response]:
        """Fetch a URL with exponential-backoff retries on transient failures.

        Retries network errors (timeouts, connection resets) and retryable
        HTTP status codes up to settings.SCRAPER_RETRY_ATTEMPTS times. Returns
        the last response received (which may be a non-2xx status the caller
        must still check) or None if every attempt raised a transport error.
        """
        attempts = max(1, settings.SCRAPER_RETRY_ATTEMPTS)
        last_response: Optional[httpx.Response] = None

        for attempt in range(1, attempts + 1):
            try:
                response = await client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                if attempt == attempts:
                    logger.error(
                        f"[{self.store_name}] {method} {url} failed after {attempts} attempts: {e}"
                    )
                    return None
                logger.warning(
                    f"[{self.store_name}] {method} {url} attempt {attempt}/{attempts} failed ({e}), retrying..."
                )
            else:
                last_response = response
                if response.status_code not in self.RETRYABLE_STATUS_CODES:
                    return response
                if attempt == attempts:
                    logger.error(
                        f"[{self.store_name}] {method} {url} still returning {response.status_code} after {attempts} attempts"
                    )
                    return response
                logger.warning(
                    f"[{self.store_name}] {method} {url} attempt {attempt}/{attempts} got status {response.status_code}, retrying..."
                )

            await asyncio.sleep(min(2 ** (attempt - 1), 10))

        return last_response

    def parse_shopify_product(self, prod: dict, default_vendor: str) -> Optional[ScrapedItem]:
        """Parse a single item from a public Shopify `products.json` feed.

        Shared by every scraper backed by the Shopify storefront API
        (gmo, karun, place_vendome), which previously each carried their own
        copy of this exact parsing logic.
        """
        try:
            prod_id = str(prod.get("id"))
            title = prod.get("title", "")
            vendor = prod.get("vendor") or default_vendor
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

            if not price_normal or price_normal <= 0:
                return None

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
                price_normal=price_normal,
                price_discount=price_discount,
                image_url=image_url,
                description=prod.get("body_html"),
                is_in_stock=in_stock,
            )
        except Exception as e:
            logger.debug(f"[{self.store_name}] Error parsing Shopify item: {e}")
            return None

    @abc.abstractmethod
    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        """Asynchronously yield scraped optical items from this store."""
        pass
