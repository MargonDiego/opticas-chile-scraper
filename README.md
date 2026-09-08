# 👓 Chilean Optics Scraper & Price Monitor API

[![CI](https://github.com/your-username/opticas-chile-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/opticas-chile-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance web scraper and REST API for tracking and comparing optical product prices across major optical retail chains in Chile.

Powered by **[uv](https://github.com/astral-sh/uv)** for fast dependency management, **[spider-rs](https://github.com/spider-rs/spider)** for high-throughput web crawling, and **FastAPI** with SQLModel for price history and querying.

---

## 🏬 Target Optical Chains in Chile

| Store Name | Domain | Platform | Target Categories |
| :--- | :--- | :--- | :--- |
| **GMO Chile** | gmo.cl | Luxottica Enterprise / Custom | Sunglasses, Eyeglasses, Contact Lenses |
| **Rotter & Krauss** | 
yk.cl / 
otterandkrauss.cl | GrandVision / VTEX / Shopify | Sunglasses, Eyeglasses, Contact Lenses |
| **Ópticas Schilling** | schilling.cl | VTEX / Custom | Sunglasses, Eyeglasses, Contact Lenses |
| **Place Vendôme** | opv.cl / placevendome.cl | VTEX / Custom | Designer Frames, Sunglasses, Lenses |
| **Econópticas** | econopticas.cl | VTEX | Budget Eyewear, Sunglasses, Contact Lenses |

---

## 🏗️ Architecture

`mermaid
flowchart TD
    subgraph CrawlerLayer [Crawler & Network Engine]
        SpiderClient[Spider-rs Rust Engine / Headless Chrome]
        HTTPClient[Async HTTPX Client with Rate-Limiting]
    end

    subgraph StoreAdapters [Optical Store Adapters]
        GMOAdapter[GMO Chile Adapter]
        RYKAdapter[Rotter & Krauss Adapter]
        SchillingAdapter[Ópticas Schilling Adapter]
        PVAdapter[Place Vendôme Adapter]
        EcoAdapter[Econópticas Adapter]
    end

    subgraph Pipeline [Data Processing & Storage]
        Normalizer[Currency & Data Normalizer]
        DB[(SQLite / PostgreSQL - Price Snapshots)]
        Scheduler[APScheduler / Cron Engine]
    end

    subgraph API [FastAPI Service]
        Endpoints[REST Endpoints / Swagger UI]
        Exports[CSV / JSON Exports]
    end

    CrawlerLayer --> StoreAdapters
    StoreAdapters --> Normalizer
    Normalizer --> DB
    Scheduler --> CrawlerLayer
    DB --> Endpoints
    DB --> Exports
`

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- [uv](https://docs.astral.sh/uv/) (Astral Python package manager)
- Python 3.10 or 3.11

### 1. Clone and Install
`ash
git clone https://github.com/your-username/opticas-chile-scraper.git
cd opticas-chile-scraper

# Install all dependencies with uv
uv sync
`

### 2. Configure Environment
`ash
cp .env.example .env
# Edit .env to adjust database paths or scrape intervals
`

### 3. Run the Service
`ash
uv run uvicorn src.main:app --reload --port 8000
`
Open [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger API documentation.

### 4. Run Tests
`ash
uv run pytest -v
`

---

## 🌐 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| GET | /api/health | Healthcheck and store scraping status. |
| GET | /api/products | Filter products by store, rand, category, price_min, price_max, search. |
| GET | /api/products/{id} | Retrieve details for a specific optical product. |
| GET | /api/products/{id}/history | Retrieve historical price snapshots for a product over time. |
| POST | /api/scrape/trigger | Trigger on-demand scrape job (store: gmo, 
yk, schilling, place_vendome, econopticas, or ll). |
| GET | /api/scrape/jobs | View background scraping job status and logs. |
| GET | /api/export/csv | Download products and latest prices as CSV. |
| GET | /api/export/json | Download products and latest prices as JSON. |

---

## 🐳 Coolify / Homelab Deployment

This project includes a production-ready Dockerfile and docker-compose.yml optimized for 1-click deployment in **Coolify** on your local server (192.168.1.85).

### Deploy via Coolify UI:
1. In Coolify, click **Create New Resource** -> **Application** -> **Public/Private Git Repository**.
2. Point to this GitHub repository.
3. Select **Docker Compose** or **Dockerfile** as build pack.
4. Set persistent storage volume:
   - Volume: opticas-data:/app/data
5. Click **Deploy**.

For detailed step-by-step instructions, see [DEPLOY_COOLIFY.md](DEPLOY_COOLIFY.md).

---

## 🏷️ GitHub Issues & Labels Taxonomy

When contributing or reporting issues, use the appropriate Issue Templates:
- **🐛 Bug Report**: General API, database, or scheduler issues.
- **🚨 Scraper Breakage**: Store layout changes, price mismatches, or bot blocks.
- **👓 New Store Request**: Proposal to add a new optical retailer in Chile.

### Labels Guide
- store:<name>: Specific store (e.g. store:gmo, store:ryk, store:schilling, store:placevendome, store:econopticas).
- 	ype:<kind>: 	ype:scraper, 	ype:api, 	ype:devops, 	ype:bug, 	ype:feature.
- priority:<level>: priority:critical, priority:high, priority:medium, priority:low.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
