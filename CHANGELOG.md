# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-08

### Added
- **PostgreSQL & `pgvector` Integration**: Switched to PostgreSQL with `pgvector/pgvector:pg16` for vector embeddings storage.
- **Ollama AI Service (`src/services/ollama.py`)**: Integration with Ollama for text embeddings (`nomic-embed-text`) and LLM chat (`llama3`).
- **Semantic Vector Search Endpoint (`POST /api/products/search/semantic`)**: Query optical products across Chilean stores by natural language similarity.
- **AI Optical Advisor Endpoint (`POST /api/advisor/chat`)**: RAG endpoint combining pgvector retrieved products with Ollama LLM recommendation.
- **Updated Docker Compose**: Multi-container stack with PostgreSQL pgvector healthcheck, network routing to Ollama, and app service.

## [0.1.0] - 2026-09-08

### Added
- Initial release of Chilean Optics Scraper & Price Monitor.
- Unified data model (`Product`, `PriceSnapshot`, `ScrapeJob`).
- Store adapters for **GMO**, **Rotter & Krauss**, **Ópticas Schilling**, **Place Vendôme**, **Econópticas**.
- FastAPI REST API with filtering, price history tracking, and CSV/JSON export.
- Background cron scheduler for automated price updates.
- Docker multi-stage build with Astral **`uv`**.
- GitHub governance: Issue templates, label taxonomy, and CI workflow.