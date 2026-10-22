"""Similarity-score mapping: pure helper plus endpoint wiring (all mocked)."""

from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.models import ProductRead
from src.services.search import cosine_distance_to_similarity


def test_cosine_distance_maps_to_similarity():
    # pgvector's <=> returns cosine distance, so 1 - 0.2 = 0.8.
    assert cosine_distance_to_similarity(0.2) == 0.8
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(1.0) == 0.0


def test_similarity_is_rounded_to_four_decimals():
    assert cosine_distance_to_similarity(0.123456) == 0.8765


def test_similarity_is_clamped_to_the_valid_range():
    assert cosine_distance_to_similarity(-0.5) == 1.0
    assert cosine_distance_to_similarity(1.5) == 0.0


def test_non_vector_rows_have_no_score():
    assert cosine_distance_to_similarity(None) is None


def _product(product_id: str, model_name: str) -> ProductRead:
    return ProductRead(
        id=product_id,
        store="gmo",
        store_product_id=product_id,
        brand="Ray-Ban",
        model_name=model_name,
        category="opticos",
        url="https://example.com/product",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    """Stands in for the pgvector candidate query; returns fixed distances."""

    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _FakeResult(self._rows)


@pytest.mark.asyncio
async def test_endpoint_populates_vector_scores_and_keeps_lexical_scores_null(monkeypatch):
    catalog = [_product("p1", "Polaroid Kids 0100"), _product("p2", "Ray-Ban Aviator")]

    async def _catalog(_session):
        return catalog, None

    async def _embedding(_text):
        return [0.01] * 8

    monkeypatch.setattr(main_module, "get_cached_catalog", _catalog)
    monkeypatch.setattr(main_module.ollama_service, "get_embedding", _embedding)
    # The statement itself is covered by test_semantic_ranking; here only the
    # scoring wiring matters, and the pgvector operator is unavailable on the
    # JSON column used by the SQLite test database.
    monkeypatch.setattr(main_module, "build_vector_search_stmt", lambda *a, **k: None)
    monkeypatch.setattr(
        main_module.settings, "DATABASE_URL", "postgresql+asyncpg://test/test"
    )

    main_module.app.dependency_overrides[main_module.get_session] = lambda: _FakeSession(
        [("p1", 0.2)]
    )
    try:
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/products/search/semantic",
                json={"query": "aviator", "limit": 10},
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()}

    assert by_id["p1"]["similarity_score"] == 0.8
    # "p2" only survived on lexical evidence, so it must not carry an invented score.
    assert by_id["p2"]["similarity_score"] is None


@pytest.mark.asyncio
async def test_null_distance_is_not_scored(monkeypatch):
    """A NULL distance must stay unscored, not become distance 1.0 -> score 0.0."""
    catalog = [_product("p1", "Polaroid Kids 0100")]

    async def _catalog(_session):
        return catalog, None

    async def _embedding(_text):
        return [0.01] * 8

    monkeypatch.setattr(main_module, "get_cached_catalog", _catalog)
    monkeypatch.setattr(main_module.ollama_service, "get_embedding", _embedding)
    monkeypatch.setattr(main_module, "build_vector_search_stmt", lambda *a, **k: None)
    monkeypatch.setattr(
        main_module.settings, "DATABASE_URL", "postgresql+asyncpg://test/test"
    )

    main_module.app.dependency_overrides[main_module.get_session] = lambda: _FakeSession(
        [("p1", None)]
    )
    try:
        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/products/search/semantic",
                json={"query": "kids 0100", "limit": 10},
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    results = response.json()
    assert results, "the lexical path must still return the row"
    # The id never entered the vector score map, so the row is lexical-only.
    assert all(item["similarity_score"] is None for item in results)


@pytest.mark.asyncio
async def test_endpoint_leaves_every_score_null_when_embeddings_are_unavailable(monkeypatch):
    catalog = [_product("p1", "Ray-Ban Aviator")]

    async def _catalog(_session):
        return catalog, None

    async def _no_embedding(_text):
        return None

    monkeypatch.setattr(main_module, "get_cached_catalog", _catalog)
    monkeypatch.setattr(main_module.ollama_service, "get_embedding", _no_embedding)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/products/search/semantic",
            json={"query": "aviator", "limit": 10},
        )

    assert response.status_code == 200
    results = response.json()
    assert results
    assert all(item["similarity_score"] is None for item in results)
