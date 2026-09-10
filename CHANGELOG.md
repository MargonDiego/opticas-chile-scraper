# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-09-10

### Added
- **Luxury Optical Product Card**: Completely overhauled `ProductCard.tsx` inspired by international luxury optical retail standards (Place Vendôme, Ray-Ban, Sunglass Hut):
  - Soft neutral gradient canvas backdrop with smooth hover zoom micro-interactions.
  - Corner-anchored category pill badges (`Sol`, `Óptico`, `Contacto`).
  - Sleek glassmorphism `Agotado` badge replacing harsh red warning boxes.
  - Transparent pricing hierarchy with explicit calculated savings (`Ahorras $X CLP`).
  - Tactile dual action buttons for price history inspection and direct store purchasing.
- **Minimalist Store Badges**: Updated `StoreBadge.tsx` with dedicated brand-accent dot indicators and clean, accessible contrast.
- **Interactive Chat Reasoning Stages**: Replaced static loading dots in `AdvisorChatWidget.tsx` with a dynamic 4-stage reasoning pipeline (Intent Analysis -> Catalog Query -> Store Price Comparison -> Recommendation Synthesis).
- **Shimmer Skeletons & Prompt Chips**: Added live shimmer preview skeletons and quick-start query chips to the AI assistant widget.
- **Full Semantic Search Filtering**: Extended `/api/products/search/semantic` and `CatalogExplorer.tsx` to support stock toggles, brand filters, deal presets (`+40% OFF`, `< $50k`), and sorting (`price-asc`, `price-desc`, `discount`, `recent`) during AI-powered vector searches.

### Changed
- **Advisor Kids vs. Adult Prioritization**: Excluded junior/kids models (`0RJ*`, `0RY9*`, `RAY-BAN JR`, `junior`, `niños`) from general searches unless explicitly requested by the user.
- **In-Stock Recommendation Priority**: Guaranteed in-stock products are ranked ahead of out-of-stock items in all advisor recommendations.
- **Performance Tuning**: Added `keep_alive: "30m"` to Ollama service calls and bounded token predictions to 55 tokens for fast, CPU-friendly inference.
- **Synced Frontend Timers**: Calibrated reasoning stage intervals to 1.9s per stage (~7.6s total) matching actual homelab CPU inference latency.

### Fixed
- **Budget Range Article Parsing**: Fixed regex in `_extract_budget_range` to correctly handle Spanish articles (e.g. `"entre los 50000 y 100000"`).
- **LLM Placeholder Token Copying**: Removed bracketed template examples from system prompts to prevent verbatim `[Marca]` or `[Tienda]` text generation.
- **Multi-word Category Parsing**: Fixed category detection to accurately map phrases like `"lentes de sol"` and `"armazones con filtro azul"`.

---

## [1.2.0] - 2026-09-10

### Added
- **Global Real-Time Stats API (`/api/stats`)**: Aggregated metrics endpoint returning catalog product counts (9,980+), active deals (4,323+), average market discount percentage (46%), and store/category distributions.
- **Integrated Live Market Ribbon**: Sleek floating status ribbon replacing bulky card widgets in `CatalogExplorer.tsx`.
- **Segmented Category Switcher**: Top segmented controller with Lucide SVG icons (`Todo`, `Sol`, `Ópticos`, `Contacto`).
- **Unified Command Search Bar**: High-contrast search input with quick deal preset pills and collapsible advanced drawer for stores and brands.

### Changed
- **Fuzzy Brand Matching**: Integrated `difflib` with 0.72 similarity cutoff to auto-correct brand typos (e.g. `"rayan"` -> `"Ray-Ban"`).
- **Natural Language Store Intent**: Added regex store alias parsing matching conversational queries like `"en gmo"` or `"de la tienda opv"`.
- **Inverted Range Normalization**: Auto-sorted inverted price constraints like `"entre 100k y 50k"` to `[50000, 100000]`.

### Fixed
- **Brand Pollution Elimination**: Removed broad fallbacks that injected foreign brands when the user explicitly queried a specific brand.

---

## [1.1.0] - 2026-09-09

### Added
- **Full Catalog Scraping Depth (9,980+ products)**:
  - **Rotter & Krauss (`ryk`)**: Added Salesforce Commerce Cloud (SFCC) pagination across `anteojos-de-sol`, `lentes-de-sol`, and `anteojos-opticos`.
  - **Schilling (`schilling`)**: Ingested full catalog across sol, armazones, and contact lenses.
  - **Econópticas (`econopticas`)**: Added deep pagination and clean CLP discount extraction.
  - **Place Vendôme (`place_vendome`)**: Combined Shopify JSON API with VTEX pub search fallback.
  - **GMO (`gmo`)**: Full Shopify catalog ingestion.
  - **Karün (`karun`)**: Full LATAM catalog scraper with test price anomaly filtering.
  - **Lentesplus (`lentesplus`)**: Implemented GraphQL catalog scraper for Chilean store.
- **Medical & Clinical Disclaimers**: Added guardrails to detect symptom queries (headaches, visual sharpness, prescriptions) and output certified ophthalmologist consult recommendations.
- **Price History Tracking**: Automated `PriceSnapshot` historical tracking on every scrape run with discount percentage calculation.

### Fixed
- **Shopify Integer Overflow**: Sanitized clean price parser to handle cent-less and decimal formatted CLP price strings.
- **Relative Image URLs**: Normalized relative paths across VTEX and SFCC endpoints to fully qualified HTTPS image URLs.
- **Frontend Tunnel Hosting**: Configured `allowedHosts` in Astro Vite configuration for Cloudflare Tunnel routing.

---

## [1.0.0] - 2026-09-08

### Added
- **FastAPI Core Backend**: RESTful API with endpoints for products, search, price history, CSV/JSON export, and manual scrape triggers.
- **PostgreSQL & pgvector**: Vector database schema for optical product embeddings and semantic similarity searches.
- **Ollama AI Advisor (`qwen2.5:1.5b` & `nomic-embed-text`)**: Self-hosted local LLM advisor client with CPU thread budgeting and greedy sampling.
- **Astro 5 + React Frontend**: High-performance static web application built with Tailwind CSS, Lucide icons, and shadcn/ui components on port 3001/3002.
- **Cybersecurity & OWASP Compliance**: API Key authentication (`X-API-Key`), strict CORS origin controls, and HTTP security response headers.
- **Docker Compose Deployment**: Containerized multi-service architecture for Coolify and homelab hosting.
