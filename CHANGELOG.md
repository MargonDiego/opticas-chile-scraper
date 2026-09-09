# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-09

### Added
- **Astro + React + shadcn/ui Frontend**: Modern web application served on port **`3001`**.
- **Interactive Catalog Explorer**: Real-time filtering by store, category, price range, and sorting.
- **pgvector Semantic Search UI**: Natural language AI search bar.
- **Price History Modal**: Timeline visualizer of historical price changes and stock availability.
- **Floating AI Advisor Chat Widget**: Real-time RAG chat connected to Ollama Qwen2.5.
- **Frontend Dockerfile**: Multi-stage Node 22 build integrated into `docker-compose.yml`.

## [0.3.0] - 2026-09-08

### Added
- API Key Authentication (`X-API-Key`).
- OWASP Security Headers Middleware & CORS hardening.
- Expanded to 7 stores (added Karün & Lentesplus).