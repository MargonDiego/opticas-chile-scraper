import csv
import io
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.config import settings
from src.database import get_session, init_db
from src.models import (
    JobStatusEnum,
    PriceSnapshot,
    PriceSnapshotRead,
    Product,
    ProductDetailRead,
    ProductRead,
    ScrapeJob,
    ScrapeTriggerRequest,
    ScrapeTriggerResponse,
    StoreEnum,
)
from src.scheduler import shutdown_scheduler, start_scheduler
from src.scrapers.registry import execute_scrape_for_store, get_available_stores

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("opticas_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Chilean Optics Scraper API...")
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down Chilean Optics Scraper API...")
    shutdown_scheduler()


app = FastAPI(
    title="👓 Chilean Optics Scraper & Price Monitor API",
    description="High-performance API to crawl, track, and compare optical product prices across major retail chains in Chile.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "available_stores": get_available_stores(),
    }


@app.get("/api/stores", tags=["Stores"])
async def list_stores():
    """List all supported optical chains."""
    return {
        "stores": [
            {"id": "gmo", "name": "GMO Chile", "url": "https://www.gmo.cl"},
            {"id": "ryk", "name": "Rotter & Krauss", "url": "https://www.rotterandkrauss.cl"},
            {"id": "schilling", "name": "Ópticas Schilling", "url": "https://schilling.cl"},
            {"id": "place_vendome", "name": "Place Vendôme", "url": "https://www.opv.cl"},
            {"id": "econopticas", "name": "Econópticas", "url": "https://www.econopticas.cl"},
        ]
    }


@app.get("/api/products", response_model=List[ProductRead], tags=["Products"])
async def get_products(
    store: Optional[str] = Query(None, description="Filter by store ID (e.g. gmo, ryk, schilling)"),
    brand: Optional[str] = Query(None, description="Filter by brand (e.g. Ray-Ban, Oakley)"),
    category: Optional[str] = Query(None, description="Filter by category (opticos, sol, contacto)"),
    search: Optional[str] = Query(None, description="Search keyword in product title/model"),
    min_price: Optional[int] = Query(None, description="Minimum price in CLP"),
    max_price: Optional[int] = Query(None, description="Maximum price in CLP"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List and search products with their latest price information."""
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

    result: List[ProductRead] = []
    for prod in products:
        latest_snapshot = None
        if prod.price_snapshots:
            # Sort snapshots by scraped_at desc
            sorted_snaps = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)
            latest_snapshot = sorted_snaps[0]

        # Apply price filters if specified
        if latest_snapshot:
            current_price = latest_snapshot.price_discount or latest_snapshot.price_normal
            if min_price and current_price < min_price:
                continue
            if max_price and current_price > max_price:
                continue

        result.append(
            ProductRead(
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
                current_price_normal=latest_snapshot.price_normal if latest_snapshot else None,
                current_price_discount=latest_snapshot.price_discount if latest_snapshot else None,
                current_in_stock=latest_snapshot.is_in_stock if latest_snapshot else None,
            )
        )

    return result


@app.get("/api/products/{product_id}", response_model=ProductDetailRead, tags=["Products"])
async def get_product_detail(
    product_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed product info including complete historical price snapshots."""
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


@app.post("/api/scrape/trigger", response_model=ScrapeTriggerResponse, tags=["Scraping"])
async def trigger_scrape(
    request: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger an on-demand scraping job for a specific optical store or all stores."""
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


@app.get("/api/scrape/jobs", response_model=List[ScrapeJob], tags=["Scraping"])
async def list_scrape_jobs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """View status and history of scraping background jobs."""
    stmt = select(ScrapeJob).order_by(ScrapeJob.started_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


@app.get("/api/export/csv", tags=["Export"])
async def export_csv(session: AsyncSession = Depends(get_session)):
    """Download all current product data with prices as a CSV file."""
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


@app.get("/api/export/json", tags=["Export"])
async def export_json(session: AsyncSession = Depends(get_session)):
    """Download all current product data with prices as JSON."""
    stmt = select(Product).options(selectinload(Product.price_snapshots))
    res = await session.execute(stmt)
    products = res.scalars().all()

    data = []
    for prod in products:
        latest = sorted(prod.price_snapshots, key=lambda s: s.scraped_at, reverse=True)[0] if prod.price_snapshots else None
        data.append({
            "id": prod.id,
            "store": prod.store,
            "brand": prod.brand,
            "model_name": prod.model_name,
            "category": prod.category,
            "price_normal": latest.price_normal if latest else None,
            "price_discount": latest.price_discount if latest else None,
            "is_in_stock": latest.is_in_stock if latest else None,
            "url": prod.url,
            "image_url": prod.image_url,
            "updated_at": prod.updated_at.isoformat() if prod.updated_at else None,
        })

    return data
