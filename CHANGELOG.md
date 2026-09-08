# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-08

### Added
- Initial release of Chilean Optics Scraper & Price Monitor.
- Unified data model (Product, PriceSnapshot, ScrapeJob) with SQLite / PostgreSQL support.
- Store scraper adapters for major Chilean optical chains:
  - **GMO Chile** (gmo.cl)
  - **Rotter & Krauss** (
yk.cl / 
otterandkrauss.cl)
  - **Ópticas Schilling** (schilling.cl)
  - **Place Vendôme** (opv.cl / placevendome.cl)
  - **Econópticas** (econopticas.cl)
- Integration with **spider-rs** high-throughput Rust crawler for dynamic JS rendering and anti-blocking crawling.
- FastAPI REST API with endpoints for filtering, search, price history tracking, and on-demand scrape triggers.
- Background cron scheduler for automated periodic price updates.
- Export endpoints for CSV and JSON data formats.
- Docker multi-stage containerization with **uv** package manager.
- Docker Compose configuration ready for 1-click deployment in **Coolify** homelab environments.
- GitHub repository governance: Issue templates (Bug, Scraper Breakage, New Store), label taxonomy, and GitHub Actions CI workflow.
