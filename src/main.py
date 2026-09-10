import csv
import difflib
import io
import json
import logging
import re
from contextlib import asynccontextmanager
from typing import List, Optional, Tuple
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings
from src.database import get_session, init_db
from src.models import (
    AdvisorChatRequest,
    AdvisorChatResponse,
    CatalogStatsRead,
    JobStatusEnum,
    PriceSnapshot,
    PriceSnapshotRead,
    Product,
    ProductDetailRead,
    ProductRead,
    ScrapeJob,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
    SemanticSearchRequest,
    SemanticSearchResult,
    StoreEnum,
)
from src.scheduler import shutdown_scheduler, start_scheduler
from src.scrapers.registry import execute_scrape_for_store, get_available_stores
from src.security import get_api_key
from src.services.ollama import ollama_service

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("opticas_api")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP Security Headers middleware."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if settings.ENABLE_SECURITY_HEADERS:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            if settings.ENVIRONMENT == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Chilean Optics Scraper & AI API...")
    await init_db()
    start_scheduler()
    yield
    logger.info("Shutting down Chilean Optics Scraper & AI API...")
    shutdown_scheduler()


app = FastAPI(
    title="👓 Chilean Optics Scraper & AI Security API",
    description="Secure, high-performance API to crawl, track, compare, and semantically query optical products across Chile with pgvector, Ollama & API Key Authentication.",
    version="0.3.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

# 1. Add Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Add CORS Middleware
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    expose_headers=["X-Total-Count"],
)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Public healthcheck for Coolify monitoring and container uptime."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "security": "api_key_enabled" if settings.API_KEY else "open_access",
        "database": "postgresql+pgvector" if settings.DATABASE_URL.startswith("postgresql") else "sqlite",
        "available_stores": get_available_stores(),
    }


@app.get("/api/stores", tags=["Stores"], dependencies=[Depends(get_api_key)])
async def list_stores():
    return {
        "stores": [
            {"id": "gmo", "name": "GMO Chile", "url": "https://gmo.cl"},
            {"id": "ryk", "name": "Rotter & Krauss", "url": "https://www.ryk.cl"},
            {"id": "schilling", "name": "Ópticas Schilling", "url": "https://www.schilling.cl"},
            {"id": "place_vendome", "name": "Place Vendôme", "url": "https://www.opv.cl"},
            {"id": "econopticas", "name": "Econópticas", "url": "https://www.econopticas.cl"},
            {"id": "karun", "name": "Karün Chile", "url": "https://karun.cl"},
            {"id": "lentesplus", "name": "Lentesplus Chile", "url": "https://www.lentesplus.com/cl"},
        ]
    }


def _map_product_read(prod: Product) -> ProductRead:
    latest = None
    if prod.price_snapshots:
        sorted_snaps = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)
        latest = sorted_snaps[0]

    return ProductRead(
        id=prod.id,
        store=prod.store,
        store_product_id=prod.store_product_id,
        brand=prod.brand,
        model_name=prod.model_name,
        category=prod.category,
        url=prod.url,
        image_url=prod.image_url,
        description=prod.description,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        current_price_normal=latest.price_normal if latest else None,
        current_price_discount=latest.price_discount if latest else None,
        current_in_stock=latest.is_in_stock if latest else None,
    )


@app.get("/api/stats", response_model=CatalogStatsRead, tags=["Catalog"], dependencies=[Depends(get_api_key)])
async def get_catalog_stats(session: AsyncSession = Depends(get_session)):
    """Return aggregated global metrics across the entire Chilean optics catalog."""
    prod_res = await session.execute(select(Product).options(selectinload(Product.price_snapshots)))
    products = prod_res.scalars().all()

    total_products = len(products)
    by_store = {}
    by_category = {}
    total_deals = 0
    total_in_stock = 0
    discount_sum = 0.0

    for prod in products:
        by_store[prod.store] = by_store.get(prod.store, 0) + 1
        by_category[prod.category] = by_category.get(prod.category, 0) + 1

        latest = None
        if prod.price_snapshots:
            sorted_snaps = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)
            latest = sorted_snaps[0]

        if latest:
            if latest.is_in_stock is not False:
                total_in_stock += 1
            if latest.price_discount and latest.price_normal and latest.price_discount < latest.price_normal:
                total_deals += 1
                pct = ((latest.price_normal - latest.price_discount) / latest.price_normal) * 100.0
                discount_sum += pct

    avg_discount = int(round(discount_sum / total_deals)) if total_deals > 0 else 0

    return CatalogStatsRead(
        total_products=total_products,
        total_deals=total_deals,
        avg_discount_percentage=avg_discount,
        total_stores=len(by_store) if by_store else len(get_available_stores()),
        total_in_stock=total_in_stock,
        by_store=by_store,
        by_category=by_category,
    )


@app.get("/api/products", response_model=List[ProductRead], tags=["Products"], dependencies=[Depends(get_api_key)])
async def get_products(
    response: Response,
    store: Optional[str] = Query(None, max_length=50, description="Filter by store ID"),
    brand: Optional[str] = Query(None, max_length=100, description="Filter by brand"),
    category: Optional[str] = Query(None, max_length=50, description="Filter by category"),
    search: Optional[str] = Query(None, max_length=150, description="Search keyword"),
    deal: Optional[str] = Query(None, description="Deal filter: disc-40, disc-20, under-50k, under-100k"),
    in_stock: Optional[bool] = Query(None, description="Filter only in stock"),
    sort_by: Optional[str] = Query("price-asc", description="Sort by: price-asc, price-desc, discount, recent"),
    min_price: Optional[int] = Query(None, ge=0, le=10000000),
    max_price: Optional[int] = Query(None, ge=0, le=10000000),
    limit: int = Query(36, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Product).options(selectinload(Product.price_snapshots))

    if store and store != "all":
        stmt = stmt.where(Product.store == store)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))
    if category and category != "all":
        stmt = stmt.where(Product.category == category)
    if search and search.strip():
        term = search.strip()
        stmt = stmt.where(or_(
            Product.model_name.ilike(f"%{term}%"),
            Product.brand.ilike(f"%{term}%"),
            Product.description.ilike(f"%{term}%"),
        ))

    res = await session.execute(stmt)
    products = res.scalars().all()

    mapped_list: List[ProductRead] = []
    for prod in products:
        mapped = _map_product_read(prod)

        # Stock filter
        if in_stock is True and mapped.current_in_stock is False:
            continue

        price = mapped.current_price_discount or mapped.current_price_normal or 0

        # Min / Max price filter
        if min_price and price < min_price:
            continue
        if max_price and price > max_price:
            continue

        # Deal filters
        if deal == "disc-40":
            if not mapped.current_price_discount or not mapped.current_price_normal:
                continue
            pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
            if pct < 40.0:
                continue
        elif deal == "disc-20":
            if not mapped.current_price_discount or not mapped.current_price_normal:
                continue
            pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
            if pct < 20.0:
                continue
        elif deal == "under-50k":
            if price <= 0 or price > 50000:
                continue
        elif deal == "under-100k":
            if price <= 0 or price > 100000:
                continue

        mapped_list.append(mapped)

    # Sorting
    if sort_by == "price-asc":
        mapped_list.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 99999999))
    elif sort_by == "price-desc":
        mapped_list.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 0), reverse=True)
    elif sort_by == "discount":
        def get_discount_pct(p: ProductRead) -> float:
            if p.current_price_discount and p.current_price_normal and p.current_price_discount < p.current_price_normal:
                return (p.current_price_normal - p.current_price_discount) / p.current_price_normal
            return 0.0
        mapped_list.sort(key=get_discount_pct, reverse=True)
    elif sort_by == "recent":
        mapped_list.sort(key=lambda p: p.updated_at, reverse=True)

    total_count = len(mapped_list)
    response.headers["X-Total-Count"] = str(total_count)

    return mapped_list[offset : offset + limit]


@app.get("/api/products/{product_id}", response_model=ProductDetailRead, tags=["Products"], dependencies=[Depends(get_api_key)])
async def get_product_detail(
    product_id: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.price_snapshots))
    res = await session.execute(stmt)
    prod = res.scalar_one_or_none()

    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    sorted_snaps = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)
    latest = sorted_snaps[0] if sorted_snaps else None

    return ProductDetailRead(
        id=prod.id,
        store=prod.store,
        store_product_id=prod.store_product_id,
        brand=prod.brand,
        model_name=prod.model_name,
        category=prod.category,
        url=prod.url,
        image_url=prod.image_url,
        description=prod.description,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        current_price_normal=latest.price_normal if latest else None,
        current_price_discount=latest.price_discount if latest else None,
        current_in_stock=latest.is_in_stock if latest else None,
        price_snapshots=[
            PriceSnapshotRead(
                id=s.id,
                price_normal=s.price_normal,
                price_discount=s.price_discount,
                discount_percentage=s.discount_percentage,
                is_in_stock=s.is_in_stock,
                scraped_at=s.scraped_at,
            )
            for s in sorted_snaps
        ],
    )


@app.post("/api/products/search/semantic", response_model=List[SemanticSearchResult], tags=["AI & Vector Search"], dependencies=[Depends(get_api_key)])
async def semantic_search(
    req: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    query_vector = await ollama_service.get_embedding(req.query)

    stmt = select(Product).options(selectinload(Product.price_snapshots))
    if req.store and req.store != "all":
        stmt = stmt.where(Product.store == req.store)
    if req.category and req.category != "all":
        stmt = stmt.where(Product.category == req.category)
    if req.brand:
        stmt = stmt.where(Product.brand.ilike(f"%{req.brand}%"))

    fetch_limit = max(req.limit * 3, 100)
    if query_vector and settings.DATABASE_URL.startswith("postgresql"):
        stmt = stmt.order_by(Product.embedding.cosine_distance(query_vector)).limit(fetch_limit)
        res = await session.execute(stmt)
        products = res.scalars().all()
    else:
        stmt = stmt.where(or_(
            Product.model_name.ilike(f"%{req.query}%"),
            Product.brand.ilike(f"%{req.query}%"),
            Product.description.ilike(f"%{req.query}%"),
        )).limit(fetch_limit)
        res = await session.execute(stmt)
        products = res.scalars().all()

    mapped_list: List[ProductRead] = []
    for prod in products:
        mapped = _map_product_read(prod)

        # Stock filter
        if req.in_stock is True and mapped.current_in_stock is False:
            continue

        price = mapped.current_price_discount or mapped.current_price_normal or 0

        # Min / Max price filter
        if req.min_price and price < req.min_price:
            continue
        if req.max_price and price > req.max_price:
            continue

        # Deal filters
        if req.deal == "disc-40":
            if not mapped.current_price_discount or not mapped.current_price_normal:
                continue
            pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
            if pct < 40.0:
                continue
        elif req.deal == "disc-20":
            if not mapped.current_price_discount or not mapped.current_price_normal:
                continue
            pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
            if pct < 20.0:
                continue
        elif req.deal == "under-50k":
            if price <= 0 or price > 50000:
                continue
        elif req.deal == "under-100k":
            if price <= 0 or price > 100000:
                continue

        mapped_list.append(mapped)

    # Sorting
    if req.sort_by == "price-asc":
        mapped_list.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 99999999))
    elif req.sort_by == "price-desc":
        mapped_list.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 0), reverse=True)
    elif req.sort_by == "discount":
        def get_discount_pct(p: ProductRead) -> float:
            if p.current_price_discount and p.current_price_normal and p.current_price_discount < p.current_price_normal:
                return (p.current_price_normal - p.current_price_discount) / p.current_price_normal
            return 0.0
        mapped_list.sort(key=get_discount_pct, reverse=True)
    elif req.sort_by == "recent":
        mapped_list.sort(key=lambda p: p.updated_at, reverse=True)

    results = []
    for mapped in mapped_list[:req.limit]:
        results.append(SemanticSearchResult(**mapped.model_dump()))
    return results


OPTICAL_STOP_WORDS = {
    "lentes", "anteojos", "gafas", "para", "busca", "buscar", "quiero",
    "necesito", "precio", "chile", "como", "unos", "unas", "del", "las",
    "los", "con", "sin", "que", "una", "uno", "por", "favor", "recomienda",
    "recomiendame", "dame", "cual", "cuales", "mejores", "mejor", "buenos",
    "bueno", "buenas", "buena", "hay", "tienen", "algo", "tipo", "estilo", "marca", "marcas",
    "pero", "mas", "más", "menos", "de", "en", "el", "la", "los", "las",
    "pa", "para", "piola", "weno", "buenisimo", "bakan", "bacanes", "onda", "unos",
    "lucas", "lucas?", "luca", "mil", "pesos", "hasta", "máximo", "maximo", "menos", "presupuesto"
}

BUDGET_CHEAP_KEYWORDS = {
    "barato", "baratos", "barata", "baratas", "barto", "bartos", "baratito", "baratitos",
    "economico", "economicos", "economica", "economicas", "oferta", "ofertas", "descuento",
    "descuentos", "rebaja", "rebajas", "liquidacion", "liquidaciones", "ganga", "gangas",
    "accesible", "accesibles", "ahorro", "barat"
}

BUDGET_EXPENSIVE_KEYWORDS = {
    "caro", "caros", "cara", "caras", "lujo", "premium", "alta gama", "top", "exclusivo", "exclusivos"
}

INTENT_CATEGORY_MAP = {
    "trekking": "sol",
    "senderismo": "sol",
    "montaña": "sol",
    "playa": "sol",
    "deporte": "sol",
    "deportivos": "sol",
    "ciclismo": "sol",
    "running": "sol",
    "sol": "sol",
    "polarizados": "sol",
    "polarizado": "sol",
    "aviador": "sol",
    "aviator": "sol",
    "armazon": "opticos",
    "armazones": "opticos",
    "marcos": "opticos",
    "marco": "opticos",
    "computador": "opticos",
    "pantalla": "opticos",
    "pantallas": "opticos",
    "oficina": "opticos",
    "pega": "opticos",
    "trabajo": "opticos",
    "laburo": "opticos",
    "filtro azul": "opticos",
    "blue defense": "opticos",
    "receta": "opticos",
    "lectura": "opticos",
    "contacto": "contacto",
    "acuvue": "contacto",
    "biofinity": "contacto",
    "astigmatismo": "contacto",
    "miopia": "contacto",
    "toricos": "contacto",
    "diarios": "contacto",
    "mensuales": "contacto",
}

INTENT_SYNONYMS = {
    "trekking": ["outdoor", "polarizad", "karun", "oakley", "arnette", "deport", "sol"],
    "senderismo": ["outdoor", "polarizad", "karun", "oakley", "sol"],
    "montaña": ["outdoor", "polarizad", "karun", "oakley", "sol"],
    "deporte": ["oakley", "arnette", "polarizad", "deport", "sol"],
    "deportivos": ["oakley", "arnette", "polarizad", "deport", "sol"],
    "ciclismo": ["oakley", "arnette", "polarizad", "sol"],
    "running": ["oakley", "polarizad", "arnette", "sol"],
    "computador": ["blue", "azul", "filtro", "optico"],
    "pantalla": ["blue", "azul", "filtro", "optico"],
    "pantallas": ["blue", "azul", "filtro", "optico"],
    "pega": ["optico", "azul", "blue", "armazon"],
    "trabajo": ["optico", "azul", "blue", "armazon"],
    "polarizados": ["polarizad", "polarizado"],
    "polarizado": ["polarizad", "polarizado"],
    "contacto": ["contacto", "acuvue", "biofinity", "soflens", "dailies"],
    "rayban": ["ray-ban", "ray ban", "aviator", "wayfarer"],
    "oakley": ["oakley", "deport", "polarizad"],
    "karun": ["karun", "sustentable", "polarizad"],
    "ecologicos": ["karun", "sustentable"],
    "ecologicas": ["karun", "sustentable"],
    "sustentables": ["karun", "sustentable"],
    "sustentable": ["karun", "sustentable"],
    "redondos": ["round", "redondo", "circular"],
    "cuadrados": ["square", "cuadrado", "rectangular"],
    "negros": ["negro", "black"],
    "dorados": ["dorado", "gold"],
    "carey": ["havana", "carey", "tortoise"],
    "havana": ["havana", "carey"],
    "transparentes": ["transparente", "clear", "cristal"],
}


STORE_ALIASES = {
    "gmo": "gmo",
    "opticas gmo": "gmo",
    "ópticas gmo": "gmo",
    "place vendome": "place_vendome",
    "place vendôme": "place_vendome",
    "opv": "place_vendome",
    "rotter": "ryk",
    "rotter & krauss": "ryk",
    "rotter y krauss": "ryk",
    "ryk": "ryk",
    "schilling": "schilling",
    "opticas schilling": "schilling",
    "ópticas schilling": "schilling",
    "econopticas": "econopticas",
    "econópticas": "econopticas",
    "karun": "karun",
    "karün": "karun",
    "lentesplus": "lentesplus",
}

BRAND_ALIASES = {
    "rayban": "Ray-Ban",
    "ray-ban": "Ray-Ban",
    "ray ban": "Ray-Ban",
    "oakley": "Oakley",
    "vogue": "Vogue",
    "karun": "Karün",
    "karün": "Karün",
    "acuvue": "Acuvue",
    "armani exchange": "Armani Exchange",
    "armani": "Armani",
    "michael kors": "Michael Kors",
    "alcon": "Alcon",
    "arnette": "Arnette",
    "burberry": "Burberry",
    "montini": "Montini",
    "biofinity": "Biofinity",
    "tecnol": "Tecnol",
    "ralph": "Ralph",
    "prada": "Prada",
    "gucci": "Gucci",
    "versace": "Versace",
    "soflens": "SofLens",
    "dailies": "Dailies",
    "carrera": "Carrera",
    "police": "Police",
    "hugo boss": "Boss",
    "boss": "Boss",
}


def _detect_store(text: str) -> Optional[str]:
    t_lower = text.lower()
    for alias, store_id in sorted(STORE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", t_lower):
            return store_id
    return None


def _detect_brand(text: str) -> Optional[str]:
    t_lower = text.lower()
    # 1. Direct match
    for alias, brand_name in sorted(BRAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in t_lower:
            return brand_name
    # 2. Fuzzy match word by word for common typos (e.g. 'rayan' -> 'Ray-Ban')
    words = [w.strip(".,;:!?\"'()") for w in t_lower.split()]
    for w in words:
        if len(w) >= 4:
            matches = difflib.get_close_matches(w, list(BRAND_ALIASES.keys()), n=1, cutoff=0.72)
            if matches:
                return BRAND_ALIASES[matches[0]]
    return None


def _parse_amount(raw: str) -> Optional[int]:
    if not raw:
        return None
    raw_clean = raw.lower().replace("$", "").replace(".", "").replace(",", "").strip()
    if "lucas" in raw_clean or "luca" in raw_clean or raw_clean.endswith("k"):
        num_str = re.sub(r"[^\d]", "", raw_clean)
        if num_str:
            return int(num_str) * 1000
    num_str = re.sub(r"[^\d]", "", raw_clean)
    if not num_str:
        return None
    val = int(num_str)
    if val < 500:
        val *= 1000
    return val


def _extract_budget_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract (min_price, max_price) in CLP from natural Spanish queries."""
    text_lower = text.lower()

    # 1. Range: 'entre los X y los Y', 'entre X y Y', 'de X a Y', 'desde X hasta Y'
    range_patterns = [
        r"(?:entre|rango\s+de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)\s+(?:y|e|a|-)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)",
        r"(?:desde|de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)\s+(?:hasta|a|-)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)",
    ]
    for pat in range_patterns:
        m = re.search(pat, text_lower)
        if m:
            min_val = _parse_amount(m.group(1))
            max_val = _parse_amount(m.group(2))
            if min_val and max_val:
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                return min_val, max_val

    # 2. Minimum only: 'sobre X', 'mas de X', 'mayor a X', 'desde X'
    min_pattern = r"(?:sobre|m[aá]s\s+de|mayor(?:es)?\s+a|desde|m[ií]nimo|m[ií]nima|a\s+partir\s+de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)"
    m_min = re.search(min_pattern, text_lower)
    min_val = _parse_amount(m_min.group(1)) if m_min else None

    # 3. Maximum only: 'menos de X', 'bajo los X', 'bajo X', 'hasta X', 'maximo X'
    max_pattern = r"(?:menos\s+de|bajo\s+(?:los\s+|las\s+)?|menor(?:es)?\s+a|hasta\s+(?:los\s+|las\s+)?|m[aá]ximo\s+(?:de\s+)?|tope\s+(?:de\s+)?|presupuesto\s+(?:de\s+)?)\s*\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)"
    m_max = re.search(max_pattern, text_lower)
    max_val = _parse_amount(m_max.group(1)) if m_max else None

    if min_val or max_val:
        return min_val, max_val

    # 4. Standalone lucas/k
    m_lucas = re.search(r"(\d+)\s*(?:lucas?|k\b)", text_lower)
    if m_lucas:
        val = int(m_lucas.group(1)) * 1000
        return None, val

    return None, None


def _detect_category(text: str) -> Optional[str]:
    """Detect optical product category from multi-word phrases and domain keywords."""
    t = text.lower()
    # 1. Contact lenses
    if any(k in t for k in ["contacto", "lentilla", "lentillas", "biofinity", "acuvue", "astigmatismo", "miopia", "toricos", "diarios", "mensuales", "soflens", "dailies"]):
        return "contacto"
    # 2. Sunglasses
    if any(k in t for k in ["lentes de sol", "anteojos de sol", "gafas de sol", "gafas solares", "sol", "polarizado", "polarizados", "polarized", "aviador", "aviator", "trekking", "senderismo", "playa", "ciclismo", "running"]):
        return "sol"
    # 3. Optical frames
    if any(k in t for k in ["lentes opticos", "lentes ópticos", "anteojos opticos", "anteojos ópticos", "armazon", "armazones", "marco", "marcos", "computador", "pantalla", "filtro azul", "blue defense", "receta", "lectura", "descanso", "pega", "trabajo", "laburo"]):
        return "opticos"
    return None


@app.post("/api/advisor/chat", response_model=AdvisorChatResponse, tags=["AI & Vector Search"], dependencies=[Depends(get_api_key)])
async def advisor_chat(
    req: AdvisorChatRequest,
    session: AsyncSession = Depends(get_session),
):
    clean_msg = req.message.lower().strip()
    raw_words = [w.strip(".,;:!?\"'()") for w in clean_msg.split()]

    # 1. Detect Budget Range (min & max in CLP)
    budget_min, budget_max = _extract_budget_range(clean_msg)

    # 2. Detect Store Intent from text or request
    target_store = req.store or _detect_store(clean_msg)

    # 3. Detect Specific Brand (with typo / fuzzy tolerance)
    detected_brand = _detect_brand(clean_msg)

    # 4. Detect Category Intent (multi-word and keyword mapping)
    inferred_category = req.category or _detect_category(clean_msg)

    # 5. Detect Stock Requirement
    stock_keywords = ["con stock", "en stock", "que haya stock", "disponible", "disponibles", "tengan stock"]
    requires_stock = any(k in clean_msg for k in stock_keywords)

    # 6. Detect Strict Deal / Discount Intent
    deal_keywords = [
        "en oferta", "con oferta", "de oferta", "ofertas", "oferta",
        "con descuento", "en descuento", "descuentos", "descuento",
        "rebajado", "rebajados", "con rebaja", "rebaja", "rebajas",
        "en promocion", "en promoción", "promociones",
        "en liquidacion", "en liquidación", "liquidacion", "liquidación"
    ]
    requires_discount = any(k in clean_msg for k in deal_keywords)

    is_cheap_intent = budget_min is not None or budget_max is not None or requires_discount or any(w in BUDGET_CHEAP_KEYWORDS or "barat" in w or "econom" in w for w in raw_words)
    is_expensive_intent = any(w in BUDGET_EXPENSIVE_KEYWORDS for w in raw_words)

    # 7. Filter meaningful product keywords
    meaningful_words = [
        w for w in raw_words
        if len(w) >= 2 and w not in OPTICAL_STOP_WORDS and w not in BUDGET_CHEAP_KEYWORDS and w not in BUDGET_EXPENSIVE_KEYWORDS
        and w not in deal_keywords and w not in stock_keywords
        and not w.isdigit()
    ]

    # Expand keywords with domain synonyms
    search_terms = list(meaningful_words)
    for w in meaningful_words:
        if w in INTENT_SYNONYMS:
            for syn in INTENT_SYNONYMS[w]:
                if syn not in search_terms:
                    search_terms.append(syn)

    query_vector = await ollama_service.get_embedding(req.message)
    stmt = select(Product).options(selectinload(Product.price_snapshots))

    if target_store:
        stmt = stmt.where(Product.store == target_store)
    if inferred_category:
        stmt = stmt.where(Product.category == inferred_category)

    # Brand filter if explicitly mentioned
    if detected_brand:
        brand_parts = detected_brand.split("-") if "-" in detected_brand else [detected_brand]
        brand_conditions = []
        for bp in brand_parts:
            brand_conditions.append(Product.brand.ilike(f"%{bp}%"))
            brand_conditions.append(Product.model_name.ilike(f"%{bp}%"))
        stmt = stmt.where(or_(*brand_conditions))
    elif search_terms:
        term_conditions = []
        for term in search_terms:
            term_conditions.append(Product.model_name.ilike(f"%{term}%"))
            term_conditions.append(Product.brand.ilike(f"%{term}%"))
            term_conditions.append(Product.description.ilike(f"%{term}%"))
        stmt = stmt.where(or_(*term_conditions))
        stmt = stmt.limit(120)
    elif query_vector and settings.DATABASE_URL.startswith("postgresql"):
        stmt = stmt.order_by(Product.embedding.cosine_distance(query_vector)).limit(80)
    else:
        stmt = stmt.order_by(Product.updated_at.desc()).limit(120)

    res = await session.execute(stmt)
    products = res.scalars().all()

    # Fallback to category products ONLY IF no specific brand and no specific store was requested
    if len(products) < 5 and inferred_category and not detected_brand and not target_store:
        fallback_stmt = (
            select(Product)
            .options(selectinload(Product.price_snapshots))
            .where(Product.category == inferred_category)
            .limit(100)
        )
        res_fb = await session.execute(fallback_stmt)
        fb_products = res_fb.scalars().all()
        existing_ids = {p.id for p in products}
        for p in fb_products:
            if p.id not in existing_ids:
                products.append(p)

    if not products:
        global_fallback = select(Product).options(selectinload(Product.price_snapshots))
        if target_store:
            global_fallback = global_fallback.where(Product.store == target_store)
        global_fallback = global_fallback.limit(100)
        res_gf = await session.execute(global_fallback)
        products = res_gf.scalars().all()

    mapped_products = [_map_product_read(p) for p in products]

    # === STRICT DETERMINISTIC PIPELINE ===

    # 1. Strict Store Filter if requested
    if target_store:
        mapped_products = [p for p in mapped_products if p.store.lower() == target_store.lower()]

    # 2. Strict Brand Matching if requested
    if detected_brand:
        d_clean = detected_brand.lower().replace("-", "").replace(" ", "")
        brand_filtered = [
            p for p in mapped_products
            if d_clean in p.brand.lower().replace("-", "").replace(" ", "") or d_clean in p.model_name.lower().replace("-", "").replace(" ", "")
        ]
        if brand_filtered:
            mapped_products = brand_filtered

    # 3. Strict Category Filter if requested or inferred
    if inferred_category:
        cat_filtered = [p for p in mapped_products if p.category == inferred_category]
        if cat_filtered:
            mapped_products = cat_filtered

    # 4. Strict Stock Requirement
    if requires_stock:
        stock_filtered = [p for p in mapped_products if p.current_in_stock is not False]
        if stock_filtered:
            mapped_products = stock_filtered

    # 5. Strict Discount / Offer Filter
    if requires_discount:
        discount_filtered = [
            p for p in mapped_products
            if p.current_price_discount is not None
            and p.current_price_normal is not None
            and p.current_price_discount < p.current_price_normal
        ]
        if discount_filtered:
            mapped_products = discount_filtered

    # 6. Strict Numeric Price Range (min and max)
    if budget_min is not None or budget_max is not None:
        range_filtered = []
        for p in mapped_products:
            price = p.current_price_discount or p.current_price_normal or 0
            if price <= 0:
                continue
            if budget_min is not None and price < budget_min:
                continue
            if budget_max is not None and price > budget_max:
                continue
            range_filtered.append(p)
        if range_filtered:
            mapped_products = range_filtered

    # 7. Sort Deterministically by Effective Price or Discount FIRST
    if is_cheap_intent or budget_min is not None or budget_max is not None:
        mapped_products.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 99999999))
    elif is_expensive_intent:
        mapped_products.sort(key=lambda p: (p.current_price_discount or p.current_price_normal or 0), reverse=True)

    # 8. Adult vs Kids Separation (Exclude junior/kids unless specifically requested)
    wants_kids = any(k in clean_msg for k in ["niño", "niña", "niños", "niñas", "hijo", "hija", "hijos", "hijas", "kids", "junior", "juvenil", "infantil"])
    def _is_kids(p: ProductRead) -> bool:
        full_text = f"{p.brand} {p.model_name} {p.description or ''}".lower()
        if any(k in full_text for k in ["junior", "juvenil", "kids", "infantil", "niño", "niña", "niños", "niñas", "años)"]):
            return True
        if re.search(r"\bjr\.?\b", full_text):
            return True
        if re.search(r"\b0?rj\d+", full_text) or re.search(r"\b0?ry9\d+", full_text):
            return True
        return False

    if not wants_kids:
        adults = [p for p in mapped_products if not _is_kids(p)]
        kids = [p for p in mapped_products if _is_kids(p)]
        mapped_products = adults if adults else kids
    else:
        kids = [p for p in mapped_products if _is_kids(p)]
        adults = [p for p in mapped_products if not _is_kids(p)]
        mapped_products = kids if kids else adults

    # 9. In-Stock Prioritization (In-stock products always appear before out-of-stock)
    in_stock_prods = [p for p in mapped_products if p.current_in_stock is not False]
    out_stock_prods = [p for p in mapped_products if p.current_in_stock is False]
    mapped_products = in_stock_prods + out_stock_prods

    # 10. Deduplicate similar model variants
    seen_model_keys = set()
    deduped_products = []
    for p in mapped_products:
        clean_model_key = re.sub(r"[^a-zA-Z0-9]", "", p.model_name[:18].lower())
        key = f"{p.store.lower()}_{p.brand.lower()}_{clean_model_key}"
        if key not in seen_model_keys:
            seen_model_keys.add(key)
            deduped_products.append(p)
        if len(deduped_products) >= 20:
            break
    mapped_products = deduped_products

    # 11. Cross-Store Diversity Ranking (Preserving best in-stock price first)
    store_best = {}
    store_remaining = []
    for p in mapped_products:
        st_key = p.store.lower()
        if st_key not in store_best:
            store_best[st_key] = p
        else:
            store_remaining.append(p)

    final_products = (list(store_best.values()) + store_remaining)[:5]

    context_lines = []
    for p in final_products:
        if p.current_price_discount and p.current_price_normal and p.current_price_discount < p.current_price_normal:
            price_str = f"${p.current_price_discount:,} CLP (Normal: ${p.current_price_normal:,} CLP, Descuento activo)"
        else:
            price_str = f"${p.current_price_normal:,} CLP"
        stock_str = "En stock" if p.current_in_stock is not False else "Sin stock"
        context_lines.append(f"- [{p.store.upper()}] {p.brand} {p.model_name} | Precio: {price_str} | Estado: {stock_str}")

    # Medical Symptom & Prescription Guardrail
    medical_terms = ["dolor", "cura", "curar", "receta", "dioptria", "dioptrías", "graduacion", "graduación", "enfermedad", "infeccion", "infección"]
    has_medical_query = any(w in medical_terms for w in raw_words) or any(t in clean_msg for t in ["me cura", "para curar", "dolor de cabeza", "receta médica"])

    context_str = "\n".join(context_lines) if context_lines else "No hay productos coincidentes cargados."

    if has_medical_query:
        ai_response = (
            "Para dolores de cabeza, síntomas visuales o determinación de graduación exacta (como tu miopía), "
            "es indispensable consultar a un oftalmólogo o tecnólogo médico para obtener tu receta oficial. "
            "A continuación te comparto opciones de armazones y lentes de contacto disponibles en el catálogo para cuando cuentes con tu receta."
        )
    else:
        ai_response = await ollama_service.ask_advisor(
            req.message,
            context_str,
            is_cheap_intent=is_cheap_intent,
            budget_min=budget_min,
            budget_max=budget_max,
            detected_brand=detected_brand,
            target_store=target_store,
            requires_discount=requires_discount,
        )

    return AdvisorChatResponse(
        response=ai_response,
        relevant_products=final_products,
    )


@app.post("/api/scrape/trigger", response_model=ScrapeTriggerResponse, tags=["Scraping"], dependencies=[Depends(get_api_key)])
async def trigger_scrape(
    request: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
):
    available = get_available_stores()
    target_stores = available if request.store == "all" else [request.store]

    for st in target_stores:
        if st not in available:
            raise HTTPException(status_code=400, detail=f"Invalid store: {st}. Available: {available}")
        background_tasks.add_task(execute_scrape_for_store, st, request.max_pages)

    return ScrapeTriggerResponse(
        message=f"Scrape triggered for stores: {', '.join(target_stores)} in background.",
        job_ids=[],
    )


@app.get("/api/scrape/jobs", response_model=List[ScrapeJob], tags=["Scraping"], dependencies=[Depends(get_api_key)])
async def list_scrape_jobs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ScrapeJob).order_by(ScrapeJob.started_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


@app.get("/api/export/csv", tags=["Export"], dependencies=[Depends(get_api_key)])
async def export_csv(session: AsyncSession = Depends(get_session)):
    stmt = select(Product).options(selectinload(Product.price_snapshots))
    res = await session.execute(stmt)
    products = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Store", "Brand", "Model Name", "Category",
        "Price Normal (CLP)", "Price Discount (CLP)", "In Stock", "URL", "Updated At"
    ])

    for prod in products:
        latest = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)[0] if prod.price_snapshots else None
        writer.writerow([
            prod.id,
            prod.store,
            prod.brand,
            prod.model_name,
            prod.category,
            latest.price_normal if latest else "",
            latest.price_discount if latest else "",
            latest.is_in_stock if latest else "",
            prod.url,
            prod.updated_at.isoformat() if prod.updated_at else "",
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opticas_chile_precios.csv"},
    )


@app.get("/api/export/json", tags=["Export"], dependencies=[Depends(get_api_key)])
async def export_json(session: AsyncSession = Depends(get_session)):
    stmt = select(Product).options(selectinload(Product.price_snapshots))
    res = await session.execute(stmt)
    products = res.scalars().all()

    data = [_map_product_read(p).model_dump() for p in products]
    return data