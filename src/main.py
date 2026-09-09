import csv
import io
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
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


@app.get("/api/products", response_model=List[ProductRead], tags=["Products"], dependencies=[Depends(get_api_key)])
async def get_products(
    store: Optional[str] = Query(None, max_length=50, description="Filter by store ID"),
    brand: Optional[str] = Query(None, max_length=100, description="Filter by brand"),
    category: Optional[str] = Query(None, max_length=50, description="Filter by category"),
    search: Optional[str] = Query(None, max_length=150, description="Search keyword"),
    min_price: Optional[int] = Query(None, ge=0, le=10000000),
    max_price: Optional[int] = Query(None, ge=0, le=10000000),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Product).options(selectinload(Product.price_snapshots))

    if store:
        stmt = stmt.where(Product.store == store)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))
    if category:
        stmt = stmt.where(Product.category == category)
    if search:
        stmt = stmt.where(Product.model_name.ilike(f"%{search}%"))

    stmt = stmt.order_by(Product.updated_at.desc()).offset(offset).limit(limit)
    res = await session.execute(stmt)
    products = res.scalars().all()

    result = []
    for prod in products:
        mapped = _map_product_read(prod)
        current_price = mapped.current_price_discount or mapped.current_price_normal
        if current_price is not None:
            if min_price and current_price < min_price:
                continue
            if max_price and current_price > max_price:
                continue
        result.append(mapped)

    return result


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
    if req.store:
        stmt = stmt.where(Product.store == req.store)
    if req.category:
        stmt = stmt.where(Product.category == req.category)

    if query_vector and settings.DATABASE_URL.startswith("postgresql"):
        stmt = stmt.order_by(Product.embedding.cosine_distance(query_vector)).limit(req.limit)
        res = await session.execute(stmt)
        products = res.scalars().all()
    else:
        stmt = stmt.where(Product.model_name.ilike(f"%{req.query}%")).limit(req.limit)
        res = await session.execute(stmt)
        products = res.scalars().all()

    results = []
    for prod in products:
        mapped = _map_product_read(prod)
        results.append(SemanticSearchResult(**mapped.model_dump()))
    return results


@app.post("/api/advisor/chat", response_model=AdvisorChatResponse, tags=["AI & Vector Search"], dependencies=[Depends(get_api_key)])
async def advisor_chat(
    req: AdvisorChatRequest,
    session: AsyncSession = Depends(get_session),
):
    query_vector = await ollama_service.get_embedding(req.message)
    stmt = select(Product).options(selectinload(Product.price_snapshots))
    if req.store:
        stmt = stmt.where(Product.store == req.store)
    if req.category:
        stmt = stmt.where(Product.category == req.category)

    if query_vector and settings.DATABASE_URL.startswith("postgresql"):
        stmt = stmt.order_by(Product.embedding.cosine_distance(query_vector)).limit(5)
    else:
        words = [w.strip() for w in req.message.split() if len(w.strip()) >= 3]
        if words:
            conditions = [
                or_(Product.model_name.ilike(f"%{w}%"), Product.brand.ilike(f"%{w}%"), Product.category.ilike(f"%{w}%"))
                for w in words
            ]
            stmt = stmt.where(or_(*conditions))
        stmt = stmt.order_by(Product.updated_at.desc()).limit(5)

    res = await session.execute(stmt)
    products = res.scalars().all()
    mapped_products = [_map_product_read(p) for p in products]

    context_lines = []
    for p in mapped_products:
        price = f"${p.current_price_discount:,} CLP (Antes: ${p.current_price_normal:,})" if p.current_price_discount else f"${p.current_price_normal:,} CLP"
        context_lines.append(f"- [{p.store.upper()}] {p.brand} {p.model_name} ({p.category}) - Precio: {price} - Link: {p.url}")

    context_str = "\n".join(context_lines) if context_lines else "No hay productos coincidentes cargados actualmente."
    ai_response = await ollama_service.ask_advisor(req.message, context_str)

    return AdvisorChatResponse(
        response=ai_response,
        relevant_products=mapped_products,
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