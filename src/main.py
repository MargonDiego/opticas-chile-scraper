import asyncio
import csv
import io
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import JSON, func, or_, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings
from src.database import async_session_factory, get_session, init_db
from src.models import (
    AdvisorChatRequest,
    AdvisorChatResponse,
    CatalogStatsRead,
    EmbeddingReindexResponse,
    PriceSnapshotRead,
    Product,
    ProductComparisonResponse,
    ProductDetailRead,
    ProductRead,
    ScrapeJob,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
    SemanticSearchRequest,
    SemanticSearchResult,
    StorePriceMatch,
)
from src.scheduler import shutdown_scheduler, start_scheduler
from src.scrapers.registry import execute_scrape_for_store, get_available_stores
from src.security import get_admin_api_key, get_api_key, RateLimitMiddleware
from src.services.advisor_nlu import (
    BUDGET_CHEAP_KEYWORDS,
    BUDGET_EXPENSIVE_KEYWORDS,
    INTENT_SYNONYMS,
    OPTICAL_STOP_WORDS,
    detect_brand,
    detect_category,
    detect_store,
    extract_budget_range,
)
from src.services.catalog import get_cached_catalog, map_product_read
from src.services.embedding_text import build_embedding_text
from src.services.ollama import ollama_service
from src.services.product_matcher import extract_canonical_key
from src.services.search import (
    apply_deal_filter,
    cosine_distance_to_similarity,
    expand_and_correct_query,
    lexical_score,
)

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

    # Pre-warm catalog cache asynchronously in background to avoid blocking startup
    async def _warm_cache():
        try:
            async with async_session_factory() as session:
                await get_cached_catalog(session)
            logger.info("Catalog cache pre-warmed successfully.")
        except Exception as e:
            logger.warning(f"Cache pre-warming failed (non-critical): {e}")

    asyncio.create_task(_warm_cache())
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

# 2. Add Rate Limiter Middleware (DDoS and AI saturation protection)
app.add_middleware(RateLimitMiddleware)

# 3. Add CORS Middleware
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
# Wildcard origins + credentials is a known CORS bypass: Starlette reflects
# the request's Origin back verbatim whenever allow_credentials=True, which
# effectively allows any origin to make authenticated cross-site requests.
allow_wildcard = "*" in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    expose_headers=["X-Total-Count"],
)


DATABASE_HEALTH_TIMEOUT_SECONDS = 2.0
OLLAMA_HEALTH_TIMEOUT_SECONDS = 1.5

# /api/health is public and explicitly exempt from the rate limiter, so the
# probe outcome is cached: without this, any caller could turn the endpoint
# into a database + Ollama I/O amplifier.
HEALTH_CACHE_TTL_SECONDS = 5.0

_health_cache: Dict[str, Any] = {
    "expires_at": 0.0,
    "status_code": 200,
    "payload": None,
}
_health_cache_lock: Optional[asyncio.Lock] = None
_health_cache_lock_loop: Optional[asyncio.AbstractEventLoop] = None


def _reset_health_cache() -> None:
    """Drop the cached health probe result. Used by test fixtures."""
    global _health_cache_lock, _health_cache_lock_loop
    _health_cache["expires_at"] = 0.0
    _health_cache["status_code"] = 200
    _health_cache["payload"] = None
    _health_cache_lock = None
    _health_cache_lock_loop = None


def _get_health_cache_lock() -> asyncio.Lock:
    """Return the probe lock, recreated when the running event loop changes.

    ``asyncio.Lock`` instances are bound to the loop that first waits on them,
    and the test suite runs every test on a fresh loop.
    """
    global _health_cache_lock, _health_cache_lock_loop
    loop = asyncio.get_running_loop()
    if _health_cache_lock is None or _health_cache_lock_loop is not loop:
        _health_cache_lock = asyncio.Lock()
        _health_cache_lock_loop = loop
    return _health_cache_lock


async def _probe_database(session: AsyncSession) -> None:
    """Run the cheapest possible round-trip against the configured database."""
    await session.execute(text("SELECT 1"))


async def _probe_health(session: AsyncSession) -> Tuple[int, Dict[str, Any]]:
    """Probe database then Ollama and return (status_code, body fields).

    A dead database is fatal (503) because the catalog cannot be served.
    A dead Ollama is only a degradation (200 + ``degraded``) because semantic
    search falls back to lexical matching and the catalog still works.
    """
    try:
        await asyncio.wait_for(_probe_database(session), timeout=DATABASE_HEALTH_TIMEOUT_SECONDS)
    except Exception as exc:
        # Only the error class is exposed: raw messages can leak DSNs/credentials.
        logger.warning("Health check: database probe failed (%s)", type(exc).__name__)
        return 503, {
            "status": "unhealthy",
            "database": "unreachable",
            "database_error": type(exc).__name__,
            "ollama": "unknown",
        }

    ollama_ok = False
    try:
        ollama_ok = await asyncio.wait_for(
            ollama_service.ping(), timeout=OLLAMA_HEALTH_TIMEOUT_SECONDS
        )
    except Exception as exc:
        logger.debug("Health check: ollama probe failed (%s)", type(exc).__name__)

    return 200, {
        "status": "healthy" if ollama_ok else "degraded",
        "database": "ok",
        "ollama": "ok" if ollama_ok else "unreachable",
    }


@app.get("/api/health", tags=["Health"])
async def health_check(session: AsyncSession = Depends(get_session)):
    """Public healthcheck for Coolify monitoring and container uptime.

    Probe results are cached for ``HEALTH_CACHE_TTL_SECONDS`` and concurrent
    hits share a single probe, so rapid polling cannot multiply I/O.
    """
    base_payload = {
        "environment": settings.ENVIRONMENT,
        "security": "api_key_enabled" if settings.API_KEY else "open_access",
        "database_engine": "postgresql+pgvector" if settings.DATABASE_URL.startswith("postgresql") else "sqlite",
        "available_stores": get_available_stores(),
    }

    def _cached_response() -> Optional[JSONResponse]:
        payload = _health_cache["payload"]
        if payload is not None and time.monotonic() < _health_cache["expires_at"]:
            return JSONResponse(
                status_code=_health_cache["status_code"],
                content={**base_payload, **payload},
            )
        return None

    cached = _cached_response()
    if cached is not None:
        return cached

    async with _get_health_cache_lock():
        # A concurrent request may have filled the cache while we waited.
        cached = _cached_response()
        if cached is not None:
            return cached

        status_code, payload = await _probe_health(session)
        _health_cache["status_code"] = status_code
        _health_cache["payload"] = payload
        _health_cache["expires_at"] = time.monotonic() + HEALTH_CACHE_TTL_SECONDS

    return JSONResponse(status_code=status_code, content={**base_payload, **payload})


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


@app.get("/api/stats", response_model=CatalogStatsRead, tags=["Catalog"], dependencies=[Depends(get_api_key)])
async def get_catalog_stats(session: AsyncSession = Depends(get_session)):
    """Return aggregated global metrics across the entire Chilean optics catalog with ultra-fast memory cache."""
    _, stats = await get_cached_catalog(session)
    return stats


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
    all_products, _ = await get_cached_catalog(session)

    filtered: List[tuple[float, ProductRead]] = []
    brand_lower = brand.lower() if brand else None

    search_tokens = []
    if search and search.strip():
        known_brands = list({p.brand for p in all_products if p.brand})
        _, search_tokens = expand_and_correct_query(search.strip(), known_brands)

    for mapped in all_products:
        if store and store != "all" and mapped.store != store:
            continue
        if category and category != "all" and mapped.category != category:
            continue
        if brand_lower and (not mapped.brand or brand_lower not in mapped.brand.lower()):
            continue

        score = lexical_score(search_tokens, mapped)
        if search_tokens and score <= 0.0:
            continue

        # Stock filter
        if in_stock is True and mapped.current_in_stock is False:
            continue

        price = mapped.current_price_discount or mapped.current_price_normal or 0

        # Min / Max price filter
        if min_price and price < min_price:
            continue
        if max_price and price > max_price:
            continue

        if not apply_deal_filter(deal, mapped, price):
            continue

        filtered.append((score, mapped))

    # Sorting
    if search_tokens and sort_by == "price-asc":
        # When user searches, prioritize relevance score first, then price
        filtered.sort(key=lambda item: (-item[0], item[1].current_price_discount or item[1].current_price_normal or 99999999))
    elif sort_by == "price-asc":
        filtered.sort(key=lambda item: (item[1].current_price_discount or item[1].current_price_normal or 99999999))
    elif sort_by == "price-desc":
        filtered.sort(key=lambda item: (item[1].current_price_discount or item[1].current_price_normal or 0), reverse=True)
    elif sort_by == "discount":
        def get_discount_pct(p: ProductRead) -> float:
            if p.current_price_discount and p.current_price_normal and p.current_price_discount < p.current_price_normal:
                return (p.current_price_normal - p.current_price_discount) / p.current_price_normal
            return 0.0
        filtered.sort(key=lambda item: get_discount_pct(item[1]), reverse=True)
    elif sort_by == "recent":
        filtered.sort(key=lambda item: item[1].updated_at, reverse=True)

    result_products = [item[1] for item in filtered]
    total_count = len(result_products)
    response.headers["X-Total-Count"] = str(total_count)

    return result_products[offset : offset + limit]


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


@app.get("/api/products/{product_id}/compare", response_model=ProductComparisonResponse, tags=["Products"], dependencies=[Depends(get_api_key)])
async def compare_product_across_stores(
    product_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Compare a given product across all Chilean optical chains using canonical model clustering."""
    all_products, _ = await get_cached_catalog(session)

    # 1. Find base product
    base_prod = next((p for p in all_products if p.id == product_id), None)
    if not base_prod:
        # Fallback to direct DB query if not in memory cache
        stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.price_snapshots))
        res = await session.execute(stmt)
        db_prod = res.scalar_one_or_none()
        if not db_prod:
            raise HTTPException(status_code=404, detail="Product not found")
        base_prod = map_product_read(db_prod)

    canonical_key, canonical_model = extract_canonical_key(base_prod)
    raw_base_price = base_prod.current_price_discount or base_prod.current_price_normal or 0
    base_effective_price = raw_base_price if (1000 <= raw_base_price <= 5000000) else 0

    # 2. Find all matches across the catalog
    matches_raw = []
    for p in all_products:
        p_key, _ = extract_canonical_key(p)
        if p_key == canonical_key:
            matches_raw.append(p)

    # 3. Build StorePriceMatch list
    matches: List[StorePriceMatch] = []
    prices: List[int] = []
    stores_present = set()

    for p in matches_raw:
        raw_eff = p.current_price_discount or p.current_price_normal
        eff_price = raw_eff if (raw_eff and 1000 <= raw_eff <= 5000000) else None
        if eff_price:
            prices.append(eff_price)
        stores_present.add(p.store)

        disc_pct = None
        if (
            p.current_price_discount
            and p.current_price_normal
            and p.current_price_discount < p.current_price_normal
            and p.current_price_discount >= 1000
        ):
            disc_pct = round(((p.current_price_normal - p.current_price_discount) / p.current_price_normal) * 100, 1)

        savings = (base_effective_price - eff_price) if (base_effective_price > 0 and eff_price) else 0

        matches.append(
            StorePriceMatch(
                product_id=p.id,
                store=p.store,
                brand=p.brand,
                model_name=p.model_name,
                url=p.url,
                image_url=p.image_url,
                price_normal=p.current_price_normal,
                price_discount=p.current_price_discount,
                effective_price=eff_price,
                discount_percentage=disc_pct,
                is_in_stock=p.current_in_stock if p.current_in_stock is not None else True,
                savings_vs_base=savings,
                is_base_product=(p.id == base_prod.id),
            )
        )

    # Sort matches: in-stock first, then lowest price first
    matches.sort(key=lambda m: (not m.is_in_stock, m.effective_price or 999999999))

    lowest_price = min(prices) if prices else None
    highest_price = max(prices) if prices else None
    max_arbitrage = (highest_price - lowest_price) if (lowest_price and highest_price) else 0
    max_arbitrage_pct = round(((highest_price - lowest_price) / highest_price) * 100, 1) if (lowest_price and highest_price and highest_price > 0) else 0.0
    cheapest_match = next((m for m in matches if m.effective_price == lowest_price), None)

    return ProductComparisonResponse(
        canonical_key=canonical_key,
        base_product_id=base_prod.id,
        brand=base_prod.brand,
        canonical_model=canonical_model,
        category=base_prod.category,
        total_stores=len(stores_present),
        total_listings=len(matches),
        cheapest_store=cheapest_match.store if cheapest_match else None,
        lowest_price=lowest_price,
        highest_price=highest_price,
        max_arbitrage_amount=max_arbitrage,
        max_arbitrage_percentage=max_arbitrage_pct,
        matches=matches,
    )



def build_vector_search_stmt(
    query_vector: List[float],
    fetch_limit: int,
    embedding_column=None,
    store: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
):
    """Build the pgvector candidate query ordered by ascending cosine distance.

    Cosine distance is 0.0 for identical vectors and grows towards 2.0, so
    ascending order puts the closest candidates first. Without the ORDER BY the
    LIMIT would return arbitrary rows instead of the best matches.

    Facet filters are pushed into SQL so a narrow facet (e.g. a single store)
    cannot spend the whole candidate budget on rows the endpoint would discard
    anyway. They mirror the Python filtering in ``semantic_search``:
    store/category are exact matches and brand is a case-insensitive substring.
    Price filters stay in Python because their values come from the latest
    price snapshot, not from the indexed product row.

    Rows without an embedding are excluded: ascending order places NULL
    distances last, and the read loop skips a NULL distance instead of scoring
    it, so an embedding-less product can never surface as a semantic hit.

    ``embedding_column`` exists so tests can compile this statement against a
    pgvector-typed column (the model column is JSON when DATABASE_URL is not
    PostgreSQL, and only pgvector columns expose ``cosine_distance``).
    """
    column = Product.embedding if embedding_column is None else embedding_column
    distance = column.cosine_distance(query_vector)

    stmt = select(Product.id, distance.label("distance")).where(Product.embedding.isnot(None))
    if store and store != "all":
        stmt = stmt.where(Product.store == store)
    if category and category != "all":
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))

    return stmt.order_by(distance.asc()).limit(fetch_limit)


@app.post("/api/products/search/semantic", response_model=List[SemanticSearchResult], tags=["AI & Vector Search"], dependencies=[Depends(get_api_key)])
async def semantic_search(
    req: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    all_products, _ = await get_cached_catalog(session)
    known_brands = list({p.brand for p in all_products if p.brand})

    # 1. Google-like Typo correction and token expansion
    corrected_query, search_tokens = expand_and_correct_query(req.query.strip(), known_brands)

    query_vector = await ollama_service.get_embedding(corrected_query)

    fetch_limit = max(req.limit * 3, 100)
    vector_results_dict: dict[str, float] = {}

    if query_vector and settings.DATABASE_URL.startswith("postgresql"):
        stmt = build_vector_search_stmt(
            query_vector,
            fetch_limit,
            store=req.store,
            category=req.category,
            brand=req.brand,
        )
        res = await session.execute(stmt)
        for row in res.all():
            p_id, dist = row[0], row[1]
            # A NULL distance is not "distance 1.0": there is no measurement to
            # score. Skipping the id keeps the row lexical-only, so it serializes
            # ``similarity_score = null`` (the documented rule) instead of a
            # fabricated 0.0.
            if dist is None:
                continue
            vector_results_dict[p_id] = float(dist)

        if not vector_results_dict:
            logger.warning(
                "Semantic search degraded to lexical-only: pgvector returned no candidates for query '%s'.",
                corrected_query,
            )
    elif query_vector is None:
        logger.warning(
            "Semantic search degraded to lexical-only: embeddings unavailable for query '%s'.",
            corrected_query,
        )
    else:
        logger.warning(
            "Semantic search degraded to lexical-only: vector search requires PostgreSQL with "
            "pgvector, but the configured database is not PostgreSQL (query '%s').",
            corrected_query,
        )

    # 2. Score across the catalog
    scored_products: List[tuple[float, ProductRead]] = []

    for mapped in all_products:
        if req.store and req.store != "all" and mapped.store != req.store:
            continue
        if req.category and req.category != "all" and mapped.category != req.category:
            continue
        if req.brand and (not mapped.brand or req.brand.lower() not in mapped.brand.lower()):
            continue

        # Hybrid score: the vector distance only applies to candidates the
        # pgvector query actually returned; lexical tokens apply everywhere.
        v_dist = vector_results_dict.get(mapped.id)
        vector_score = max(0.0, (1.0 - v_dist) * 80.0) if v_dist is not None else 0.0

        total_score = lexical_score(search_tokens, mapped) + vector_score
        if vector_results_dict:
            # Vector ranking is authoritative: rows outside the vector
            # candidate set only survive on lexical evidence.
            if total_score <= 0.0 and mapped.id not in vector_results_dict:
                continue

        # Stock filter
        if req.in_stock is True and mapped.current_in_stock is False:
            continue

        price = mapped.current_price_discount or mapped.current_price_normal or 0

        # Min / Max price filter
        if req.min_price and price < req.min_price:
            continue
        if req.max_price and price > req.max_price:
            continue

        if not apply_deal_filter(req.deal, mapped, price):
            continue

        scored_products.append((total_score, mapped))

    # Sorting
    if req.sort_by == "price-asc":
        scored_products.sort(key=lambda item: (-item[0], item[1].current_price_discount or item[1].current_price_normal or 99999999))
    elif req.sort_by == "price-desc":
        scored_products.sort(key=lambda item: (item[1].current_price_discount or item[1].current_price_normal or 0), reverse=True)
    elif req.sort_by == "discount":
        def get_discount_pct(p: ProductRead) -> float:
            if p.current_price_discount and p.current_price_normal and p.current_price_discount < p.current_price_normal:
                return (p.current_price_normal - p.current_price_discount) / p.current_price_normal
            return 0.0
        scored_products.sort(key=lambda item: get_discount_pct(item[1]), reverse=True)
    elif req.sort_by == "recent":
        scored_products.sort(key=lambda item: item[1].updated_at, reverse=True)
    else:
        scored_products.sort(key=lambda item: -item[0])

    results = []
    for _, mapped in scored_products[:req.limit]:
        result = SemanticSearchResult(**mapped.model_dump())
        # pgvector's ``<=>`` operator returns cosine distance, so the honest
        # score is ``similarity = 1 - distance`` clamped to [0.0, 1.0] and
        # rounded to 4 decimals. Only rows that came back from the vector
        # candidate set have a measurable distance; lexical-only fallback rows
        # keep ``similarity_score = None`` instead of inventing a number.
        distance = vector_results_dict.get(mapped.id)
        if distance is not None:
            result.similarity_score = cosine_distance_to_similarity(distance)
        results.append(result)
    return results



@app.post("/api/advisor/chat", response_model=AdvisorChatResponse, tags=["AI & Vector Search"], dependencies=[Depends(get_api_key)])
async def advisor_chat(
    req: AdvisorChatRequest,
    session: AsyncSession = Depends(get_session),
):
    clean_msg = req.message.lower().strip()
    raw_words = [w.strip(".,;:!?\"'()") for w in clean_msg.split()]

    # 1. Detect Budget Range (min & max in CLP)
    budget_min, budget_max = extract_budget_range(clean_msg)

    # 2. Detect Store Intent from text or request
    target_store = req.store or detect_store(clean_msg)

    # 3. Detect Specific Brand (with typo / fuzzy tolerance)
    detected_brand = detect_brand(clean_msg)

    # 4. Detect Category Intent (multi-word and keyword mapping)
    inferred_category = req.category or detect_category(clean_msg)

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

    mapped_products = [map_product_read(p) for p in products]

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


@app.post("/api/scrape/trigger", response_model=ScrapeTriggerResponse, tags=["Scraping"], dependencies=[Depends(get_admin_api_key)])
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


@app.get("/api/scrape/jobs", response_model=List[ScrapeJob], tags=["Scraping"], dependencies=[Depends(get_admin_api_key)])
async def list_scrape_jobs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ScrapeJob).order_by(ScrapeJob.started_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


@app.get("/api/export/csv", tags=["Export"], dependencies=[Depends(get_admin_api_key)])
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


@app.get("/api/export/json", tags=["Export"], dependencies=[Depends(get_admin_api_key)])
async def export_json(session: AsyncSession = Depends(get_session)):
    stmt = select(Product).options(selectinload(Product.price_snapshots))
    res = await session.execute(stmt)
    products = res.scalars().all()

    data = [map_product_read(p).model_dump() for p in products]
    return data


# --- Admin embedding re-index -------------------------------------------------
#
# Rebuilding embeddings is an opt-in maintenance task. Two guards matter:
#
# * It must not pin a pooled database connection while Ollama works. The batch
#   is read through a short-lived session, embedded with no session checked
#   out, and persisted through a second short-lived session.
# * Two operators paging the endpoint at once would double the work, so a
#   module-level lock rejects a concurrent run with 409.
#
# The lock is recreated when the event loop changes, for the same reason as the
# health probe lock: ``asyncio.Lock`` binds to the loop that first waits on it
# and the test suite runs every test on a fresh loop.
_reindex_lock: Optional[asyncio.Lock] = None
_reindex_lock_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_reindex_lock() -> asyncio.Lock:
    """Return the re-index lock for the running event loop."""
    global _reindex_lock, _reindex_lock_loop
    loop = asyncio.get_running_loop()
    if _reindex_lock is None or _reindex_lock_loop is not loop:
        _reindex_lock = asyncio.Lock()
        _reindex_lock_loop = loop
    return _reindex_lock


def _missing_embedding_clause():
    """Match products whose embedding has not been computed yet.

    PostgreSQL stores a real SQL NULL in the pgvector column, so ``IS NULL`` is
    enough. The SQLite fallback stores the column as JSON, where SQLAlchemy
    serializes a Python ``None`` as the JSON literal ``null`` instead of SQL
    NULL; without the extra comparison a local ``only_missing`` run would match
    nothing at all.
    """
    column = Product.__table__.c.embedding
    if isinstance(column.type, JSON):
        return or_(column.is_(None), column == JSON.NULL)
    return column.is_(None)


def _reindex_filters(*, only_missing: bool = False, store: Optional[str] = None) -> List[Any]:
    """Filters shared by the batch read and the ``remaining`` count.

    Both statements MUST use this helper: if they ever diverge, ``done`` starts
    describing a different set than the one that was actually processed.
    """
    filters: List[Any] = []
    if store:
        filters.append(Product.store == store)
    if only_missing:
        filters.append(_missing_embedding_clause())
    return filters


def build_reindex_batch_stmt(
    *,
    limit: int,
    after_id: Optional[str] = None,
    only_missing: bool = False,
    store: Optional[str] = None,
):
    """One keyset page of products to re-index.

    ``id > :after_id ORDER BY id LIMIT :limit`` replaces OFFSET paging: it is
    deterministic under concurrent inserts/deletes and it can never re-read the
    same page when processed rows leave the filtered set (``only_missing``). The
    cursor is exclusive, so the row it points at is never processed twice.

    The primary key is a string (``gmo:123``), so the comparison is a text range
    scan over the primary-key index rather than a numeric one.
    """
    stmt = select(
        Product.id,
        Product.brand,
        Product.model_name,
        Product.category,
        Product.store,
        Product.description,
    )
    for clause in _reindex_filters(only_missing=only_missing, store=store):
        stmt = stmt.where(clause)
    if after_id:
        stmt = stmt.where(Product.id > after_id)
    return stmt.order_by(Product.id).limit(limit)


def build_reindex_remaining_stmt(
    *,
    only_missing: bool = False,
    store: Optional[str] = None,
    after_id: Optional[str] = None,
):
    """``COUNT(*)`` of the rows that still need work after this batch.

    Both modes count "work left", which is what makes ``done = remaining == 0``
    meaningful:

    * ``only_missing``: the filters already describe the outstanding work
      (``embedding IS NULL``), so the count is cursor-independent. A row that
      keeps failing stays counted, so ``done`` can never claim success while the
      catalog still has NULL embeddings.
    * full re-index: nothing in the row changes, so the outstanding work is the
      part of the scan that has not been paged yet. The caller therefore passes
      the cursor here; without that bound ``remaining`` would be the catalog
      size and ``done`` could never become true.
    """
    stmt = select(func.count()).select_from(Product)
    for clause in _reindex_filters(only_missing=only_missing, store=store):
        stmt = stmt.where(clause)
    if after_id:
        stmt = stmt.where(Product.id > after_id)
    return stmt


@app.post(
    "/api/admin/embeddings/reindex",
    response_model=EmbeddingReindexResponse,
    tags=["Admin"],
    dependencies=[Depends(get_admin_api_key)],
)
async def reindex_embeddings(
    limit: int = Query(100, ge=1, le=500, description="Products per batch"),
    after_id: Optional[str] = Query(
        None,
        max_length=200,
        description=(
            "Exclusive keyset cursor: the next_cursor of the previous batch. "
            "Omit it for the first batch."
        ),
    ),
    only_missing: bool = Query(
        False, description="Process only products whose embedding is NULL"
    ),
    store: Optional[str] = Query(None, max_length=50, description="Restrict to one store"),
):
    """Rebuild product embeddings after the embedding text composition changes.

    Keyset paging contract:

    * First call sends no ``after_id``; every later call sends the previous
      ``next_cursor``. ``next_cursor`` is the last id *attempted* in the batch,
      so it always advances, even when some rows failed and stayed NULL.
    * Stop when ``done`` is true, or when a batch returns ``processed == 0``
      while ``remaining`` is still non-zero (the leftovers keep failing; they
      are logged row by row). Never re-send the same cursor in a loop.
    * ``remaining`` is a real ``COUNT(*)`` measured after this batch was
      written, and ``done`` is exactly ``remaining == 0``. With
      ``only_missing`` it counts rows still matching the filters (NULL
      embeddings) anywhere, so a row that keeps failing keeps ``done`` false.
      In a full sweep it counts the scan ahead of the cursor, so ``done``
      becomes true once the last page has been processed.
    * ``updated`` is the UPDATE rowcount, so a row deleted between the read and
      the write phase is not counted as updated.
    * A batch where every row that had text produced no vector at all is an
      outage, not a partial success: it returns 503 so the operator stops and
      fixes the embedding service instead of burning through the catalog.
    """
    lock = _get_reindex_lock()
    if lock.locked():
        raise HTTPException(
            status_code=409,
            detail=(
                "An embedding re-index is already running. "
                "Wait for the current batch to finish before starting another one."
            ),
        )

    # There is no suspension point between ``locked()`` and this acquire on a
    # single event loop, so the check-then-acquire is atomic. try/finally (not
    # ``async with``) keeps the release explicit on every exit path, including
    # HTTPException, cancellation and unexpected errors.
    await lock.acquire()
    try:
        # Phase 1: read the batch, then release the connection.
        async with async_session_factory() as session:
            rows = (
                await session.execute(
                    build_reindex_batch_stmt(
                        limit=limit,
                        after_id=after_id,
                        only_missing=only_missing,
                        store=store,
                    )
                )
            ).all()

        # Phase 2: embed with no database session checked out.
        vectors: List[Tuple[str, List[float]]] = []
        attempted_ids: List[str] = []
        failed_no_text = 0
        failed_embedding = 0
        for product_id, brand, model_name, category, prod_store, description in rows:
            attempted_ids.append(product_id)
            text = build_embedding_text(
                brand=brand,
                model_name=model_name,
                category=category,
                store=prod_store,
                description=description,
            )
            if not text:
                logger.warning(
                    "Skipping re-index for product %s: empty embedding text.", product_id
                )
                failed_no_text += 1
                continue

            vector = await ollama_service.get_embedding(text)
            if not vector:
                logger.warning("Re-index could not embed product %s.", product_id)
                failed_embedding += 1
                continue

            vectors.append((product_id, vector))

        rows_with_text = len(rows) - failed_no_text
        if rows_with_text and failed_embedding == rows_with_text:
            # Ollama answered nothing for every embeddable row: this is an
            # unreachable embedding service, not a partial success. Failing
            # loudly keeps the operator from sweeping the catalog to NULL.
            raise HTTPException(
                status_code=503,
                detail=(
                    "Embedding service unavailable: none of the "
                    f"{rows_with_text} embeddable products in this batch produced a vector. "
                    "No embeddings were written. Check Ollama (OLLAMA_BASE_URL) and retry "
                    f"the same cursor (after_id={after_id!r}, only_missing={only_missing}, "
                    f"store={store!r})."
                ),
            )

        # Phase 3: persist through a second short-lived session.
        updated = 0
        if vectors:
            try:
                async with async_session_factory() as session:
                    for product_id, vector in vectors:
                        result = await session.execute(
                            update(Product)
                            .where(Product.id == product_id)
                            .values(embedding=vector)
                        )
                        # The rowcount, not len(vectors): a row deleted between
                        # the read and the write phase matches nothing and must
                        # not be reported as updated.
                        updated += result.rowcount or 0
                    await session.commit()
            except Exception:
                logger.error(
                    "Re-index failed while persisting vectors (after_id=%s).",
                    after_id,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Could not persist the embeddings of this batch; nothing was "
                        "committed. Retry the same cursor."
                    ),
                ) from None

        processed = len(rows)
        next_cursor = attempted_ids[-1] if attempted_ids else after_id

        # ``remaining`` is measured after the write, so it reflects the rows this
        # batch just fixed instead of the state the batch started from.
        # In only_missing mode the filters already express the outstanding work,
        # so the cursor must NOT shrink the count (a persistently failing row
        # must keep ``done`` false). In a full sweep the outstanding work is the
        # scan ahead of the cursor.
        async with async_session_factory() as session:
            remaining = int(
                (
                    await session.execute(
                        build_reindex_remaining_stmt(
                            only_missing=only_missing,
                            store=store,
                            after_id=None if only_missing else next_cursor,
                        )
                    )
                ).scalar_one()
            )

        done = remaining == 0

        if processed == 0 and not done:
            logger.warning(
                "Embedding re-index reached the end of the scan with %s rows still "
                "unembedded; they keep failing (see the per-row warnings above).",
                remaining,
            )

        logger.info(
            "Embedding re-index batch: after_id=%s limit=%s only_missing=%s store=%s "
            "processed=%s updated=%s failed_no_text=%s failed_embedding=%s "
            "remaining=%s done=%s",
            after_id,
            limit,
            only_missing,
            store,
            processed,
            updated,
            failed_no_text,
            failed_embedding,
            remaining,
            done,
        )

        return EmbeddingReindexResponse(
            processed=processed,
            updated=updated,
            failed_no_text=failed_no_text,
            failed_embedding=failed_embedding,
            remaining=remaining,
            next_cursor=next_cursor,
            done=done,
        )
    finally:
        lock.release()