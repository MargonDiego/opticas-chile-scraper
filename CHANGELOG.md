# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-09-08

### Added
- **API Key Authentication**: `X-API-Key` header verification using constant-time comparison (`secrets.compare_digest`) against timing attacks.
- **OWASP Security Headers Middleware**: Automatic injection of `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, and `Strict-Transport-Security`.
- **CORS Hardening**: Configurable `CORS_ORIGINS` to prevent cross-site request forgery.
- **Input Validation & Sanitization**: Query parameter bounds and length limits on search endpoints to prevent resource exhaustion / DoS.
- **Expanded Optical Coverage (7 Stores)**: Added adapters for **Karün Chile** (`karun`) and **Lentesplus Chile** (`lentesplus`), and refined **Ópticas Schilling** and **Econópticas** parsers.
- **Security Test Suite**: Dedicated tests for unauthorized 401/403 rejections, healthcheck bypass, and security headers.

## [0.2.0] - 2026-09-08

### Added
- PostgreSQL & `pgvector` Integration for vector embeddings storage.
- Ollama AI Service for text embeddings (`nomic-embed-text`) and LLM chat (`qwen2.5:1.5b`).
- Semantic Vector Search (`POST /api/products/search/semantic`).
- AI Optical Advisor Endpoint (`POST /api/advisor/chat`).

## [0.1.0] - 2026-09-08

### Added
- Initial release of Chilean Optics Scraper & Price Monitor.