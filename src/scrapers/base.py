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

    @abc.abstractmethod
    async def scrape_catalog(
        self, max_pages: Optional[int] = None
    ) -> AsyncGenerator[ScrapedItem, None]:
        """Asynchronously yield scraped optical items from this store."""
        pass
