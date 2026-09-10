from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, Relationship, SQLModel
from src.config import settings

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class StoreEnum(str, Enum):
    GMO = "gmo"
    ROTTER_KRAUSS = "ryk"
    SCHILLING = "schilling"
    PLACE_VENDOME = "place_vendome"
    ECONOPTICAS = "econopticas"
    KARUN = "karun"
    LENTESPLUS = "lentesplus"


class CategoryEnum(str, Enum):
    OPTICOS = "opticos"
    SOL = "sol"
    CONTACTO = "contacto"
    ACCESORIOS = "accesorios"
    OTRO = "otro"


class JobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# SQLModel Database Tables
class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: str = Field(primary_key=True)
    store: str = Field(index=True)
    store_product_id: str = Field(index=True)
    brand: str = Field(index=True)
    model_name: str
    category: str = Field(default=CategoryEnum.OTRO.value, index=True)
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    
    embedding: Optional[Any] = Field(
        default=None,
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
        if HAS_PGVECTOR and settings.DATABASE_URL.startswith("postgresql")
        else Column(JSON, nullable=True),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    price_snapshots: List["PriceSnapshot"] = Relationship(
        back_populates="product",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class PriceSnapshot(SQLModel, table=True):
    __tablename__ = "price_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    price_normal: int = Field(index=True)
    price_discount: Optional[int] = None
    discount_percentage: Optional[float] = None
    is_in_stock: bool = Field(default=True)
    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    product: Optional[Product] = Relationship(back_populates="price_snapshots")


class ScrapeJob(SQLModel, table=True):
    __tablename__ = "scrape_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    store: str = Field(index=True)
    status: str = Field(default=JobStatusEnum.PENDING.value, index=True)
    items_scraped: int = Field(default=0)
    items_updated: int = Field(default=0)
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class PriceSnapshotRead(SQLModel):
    id: int
    price_normal: int
    price_discount: Optional[int] = None
    discount_percentage: Optional[float] = None
    is_in_stock: bool
    scraped_at: datetime


class ProductRead(SQLModel):
    id: str
    store: str
    store_product_id: str
    brand: str
    model_name: str
    category: str
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    current_price_normal: Optional[int] = None
    current_price_discount: Optional[int] = None
    current_in_stock: Optional[bool] = None


class ProductDetailRead(ProductRead):
    price_snapshots: List[PriceSnapshotRead] = []


class SemanticSearchRequest(SQLModel):
    query: str
    store: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    deal: Optional[str] = None
    in_stock: Optional[bool] = None
    sort_by: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    limit: int = 60


class SemanticSearchResult(ProductRead):
    similarity_score: Optional[float] = None


class AdvisorChatRequest(SQLModel):
    message: str
    store: Optional[str] = None
    category: Optional[str] = None


class AdvisorChatResponse(SQLModel):
    response: str
    relevant_products: List[ProductRead] = []


class ScrapeTriggerRequest(SQLModel):
    store: str = "all"
    max_pages: Optional[int] = None


class ScrapeTriggerResponse(SQLModel):
    message: str
    job_ids: List[int]


class CatalogStatsRead(SQLModel):
    total_products: int
    total_deals: int
    avg_discount_percentage: int
    total_stores: int
    total_in_stock: int
    by_store: dict
    by_category: dict