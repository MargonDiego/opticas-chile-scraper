"""Tests for POST /api/admin/embeddings/reindex: auth, keyset paging, lock."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.future import select

import src.main as main_module
from src.config import settings
from src.database import async_session_factory
from src.main import build_reindex_batch_stmt, build_reindex_remaining_stmt
from src.models import Product
from src.services.ollama import ollama_service

ADMIN_KEY = "test-admin-key"
ENDPOINT = "/api/admin/embeddings/reindex"
VECTOR = [0.02] * 8


def _make_product(
    product_id: str,
    *,
    store: str = "gmo",
    brand: str = "Ray-Ban",
    model_name: str = "Aviator",
    category: str = "opticos",
    description: str = "Lentes de sol.",
    embedding=None,
) -> Product:
    return Product(
        id=product_id,
        store=store,
        store_product_id=product_id,
        brand=brand,
        model_name=model_name,
        category=category,
        url=f"https://example.com/{product_id}",
        description=description,
        embedding=embedding,
    )


async def _seed(*products: Product) -> None:
    async with async_session_factory() as session:
        for product in products:
            session.add(product)
        await session.commit()


async def _read_embeddings(product_ids: list[str]) -> dict:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Product.id, Product.embedding).where(Product.id.in_(product_ids))
        )
        return {product_id: embedding for product_id, embedding in result.all()}


@pytest.fixture
def admin_key(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
    return ADMIN_KEY


@pytest.fixture
def embedding_calls(monkeypatch):
    calls: list[str] = []

    async def _fake_embedding(text: str):
        calls.append(text)
        return list(VECTOR)

    monkeypatch.setattr(ollama_service, "get_embedding", _fake_embedding)
    return calls


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test")


async def _batch(client: AsyncClient, headers: dict, **params) -> dict:
    response = await client.post(ENDPOINT, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_reindex_requires_admin_auth(admin_key, embedding_calls):
    async with _client() as client:
        missing = await client.post(ENDPOINT)
        wrong = await client.post(ENDPOINT, headers={"X-API-Key": "wrong-key"})
        allowed = await client.post(ENDPOINT, headers={"X-API-Key": admin_key})

    assert missing.status_code == 401
    assert wrong.status_code == 403
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_reindex_pages_with_a_keyset_cursor(admin_key, embedding_calls):
    await _seed(*[_make_product(f"p{i:02d}") for i in range(5)])
    headers = {"X-API-Key": admin_key}

    async with _client() as client:
        first = await _batch(client, headers, limit=2)
        second = await _batch(client, headers, limit=2, after_id=first["next_cursor"])
        third = await _batch(client, headers, limit=2, after_id=second["next_cursor"])

    assert first == {
        "processed": 2,
        "updated": 2,
        "failed_no_text": 0,
        "failed_embedding": 0,
        "remaining": 3,
        "next_cursor": "p01",
        "done": False,
    }
    assert second["processed"] == 2
    assert second["next_cursor"] == "p03"
    assert second["remaining"] == 1
    assert second["done"] is False
    # The trailing partial page is what actually finishes the run.
    assert third["processed"] == 1
    assert third["updated"] == 1
    assert third["next_cursor"] == "p04"
    assert third["remaining"] == 0
    assert third["done"] is True

    saved = await _read_embeddings(["p00", "p01", "p04"])
    assert all(embedding is not None for embedding in saved.values())
    assert len(embedding_calls) == 5


@pytest.mark.asyncio
async def test_reindex_cursor_is_exclusive_and_stable_under_deletes(
    admin_key, embedding_calls
):
    """A row deleted between batches must not shift the next page."""
    await _seed(
        *[
            _make_product(f"p{i:02d}", model_name=f"Model {i}")
            for i in range(5)
        ]
    )
    headers = {"X-API-Key": admin_key}

    async with _client() as client:
        first = await _batch(client, headers, limit=2)
        async with async_session_factory() as session:
            # Removing an already-page'd row is harmless; removing a future row
            # must simply shrink the next page instead of re-reading or skipping.
            await session.execute(delete(Product).where(Product.id == "p02"))
            await session.commit()
        second = await _batch(client, headers, limit=2, after_id=first["next_cursor"])

    assert first["next_cursor"] == "p01"
    # OFFSET paging would have read p03,p04 here and skipped nothing; keyset
    # must resume strictly after p01 and see p03 (p02 is gone).
    assert second["processed"] == 2
    assert any("Model 3" in text for text in embedding_calls)
    assert any("Model 4" in text for text in embedding_calls)
    assert all("Model 2" not in text for text in embedding_calls[2:])


@pytest.mark.asyncio
async def test_reindex_only_missing_skips_products_with_a_vector(admin_key, embedding_calls):
    await _seed(
        _make_product("has-vector", embedding=list(VECTOR)),
        _make_product("missing-1"),
        _make_product("missing-2"),
    )

    async with _client() as client:
        body = await _batch(
            client, {"X-API-Key": admin_key}, only_missing="true", limit=10
        )

    assert body["processed"] == 2
    assert body["updated"] == 2
    # Processed rows leave the filtered set, so the real count is now zero.
    assert body["remaining"] == 0
    assert body["done"] is True
    assert body["next_cursor"] == "missing-2"


@pytest.mark.asyncio
async def test_reindex_keeps_paging_past_rows_that_keep_failing(admin_key, embedding_calls):
    """Reproduces the old infinite loop: a page of rows that stay NULL."""
    await _seed(
        _make_product("a-good"),
        _make_product(
            "b-empty", store="", brand="", model_name="", category="", description=None
        ),
    )
    headers = {"X-API-Key": admin_key}

    async with _client() as client:
        first = await _batch(client, headers, limit=1, only_missing="true")
        second = await _batch(
            client, headers, limit=1, only_missing="true", after_id=first["next_cursor"]
        )
        third = await _batch(
            client, headers, limit=1, only_missing="true", after_id=second["next_cursor"]
        )

    assert first["updated"] == 1
    assert first["remaining"] == 1
    assert first["done"] is False

    # The permanently failing row is attempted, then the cursor moves past it.
    assert second["processed"] == 1
    assert second["failed_no_text"] == 1
    assert second["next_cursor"] == "b-empty"
    # done must stay honest: one row is still missing an embedding.
    assert second["remaining"] == 1
    assert second["done"] is False

    # The scan is exhausted (processed == 0), so the caller stops here instead
    # of re-reading the same failing page forever.
    assert third["processed"] == 0
    assert third["remaining"] == 1
    assert third["next_cursor"] == "b-empty"
    assert third["done"] is False


@pytest.mark.asyncio
async def test_reindex_returns_503_and_releases_the_lock_when_ollama_is_down(
    admin_key, monkeypatch
):
    await _seed(_make_product("p00"), _make_product("p01"))

    async def _no_vector(_text):
        return None

    monkeypatch.setattr(ollama_service, "get_embedding", _no_vector)

    async with _client() as client:
        response = await client.post(ENDPOINT, headers={"X-API-Key": admin_key})

    assert response.status_code == 503
    assert "Embedding service unavailable" in response.json()["detail"]
    # Nothing was written and the run lock is free again for the retry.
    saved = await _read_embeddings(["p00", "p01"])
    assert all(embedding is None for embedding in saved.values())
    assert main_module._get_reindex_lock().locked() is False


@pytest.mark.asyncio
async def test_reindex_counts_only_rows_actually_written(admin_key, monkeypatch):
    """A row deleted between the read and the write phase is not "updated"."""
    await _seed(_make_product("p00"), _make_product("p01"))

    async def _embedding_then_delete(text: str):
        async with async_session_factory() as session:
            await session.execute(delete(Product).where(Product.id == "p01"))
            await session.commit()
        return list(VECTOR)

    monkeypatch.setattr(ollama_service, "get_embedding", _embedding_then_delete)

    async with _client() as client:
        response = await client.post(ENDPOINT, headers={"X-API-Key": admin_key})

    body = response.json()
    assert body["processed"] == 2
    # The UPDATE for p01 matched zero rows, so the rowcount is 1, not len(vectors).
    assert body["updated"] == 1
    assert body["remaining"] == 0
    assert body["done"] is True


@pytest.mark.asyncio
async def test_reindex_store_filter_limits_the_batch(admin_key, embedding_calls):
    await _seed(_make_product("gmo-1", store="gmo"), _make_product("ryk-1", store="ryk"))

    async with _client() as client:
        body = await _batch(client, {"X-API-Key": admin_key}, store="gmo")

    assert body["processed"] == 1
    assert body["remaining"] == 0
    saved = await _read_embeddings(["gmo-1", "ryk-1"])
    assert saved["gmo-1"] is not None
    assert saved["ryk-1"] is None


@pytest.mark.asyncio
async def test_reindex_skips_products_with_empty_embedding_text(admin_key, embedding_calls):
    await _seed(
        _make_product(
            "empty", store="", brand="", model_name="", category="", description=None
        )
    )

    async with _client() as client:
        response = await client.post(ENDPOINT, headers={"X-API-Key": admin_key})

    body = response.json()
    assert body["processed"] == 1
    assert body["updated"] == 0
    assert body["failed_no_text"] == 1
    assert body["failed_embedding"] == 0
    # Empty text is "nothing to embed", not an outage: 200, not 503.
    assert response.status_code == 200
    # Empty text must never reach Ollama.
    assert embedding_calls == []


@pytest.mark.asyncio
async def test_reindex_returns_409_when_a_run_is_in_progress(admin_key, embedding_calls):
    lock = main_module._get_reindex_lock()
    await lock.acquire()
    try:
        async with _client() as client:
            response = await client.post(ENDPOINT, headers={"X-API-Key": admin_key})
    finally:
        lock.release()

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]


def test_reindex_batch_query_is_keyset_with_filters_before_the_limit():
    """Regression: OFFSET paging re-read the same page in only_missing mode."""
    stmt = build_reindex_batch_stmt(
        limit=100, after_id="gmo:100", only_missing=True, store="gmo"
    )
    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "OFFSET" not in sql
    where_index = sql.index("WHERE")
    order_index = sql.index("ORDER BY")
    limit_index = sql.index("LIMIT")
    assert where_index < order_index < limit_index

    where_clause = sql[where_index:order_index]
    assert "products.id > " in where_clause
    assert "products.store =" in where_clause
    assert "products.embedding IS NULL" in where_clause
    # The cursor is the last ORDER BY key, so the page is deterministic.
    assert "ORDER BY products.id" in sql


def test_reindex_remaining_count_uses_the_same_filters_without_a_cursor():
    sql = str(
        build_reindex_remaining_stmt(only_missing=True, store="gmo").compile(
            dialect=postgresql.dialect()
        )
    )

    assert "count(*)" in sql.lower()
    assert "LIMIT" not in sql
    assert "OFFSET" not in sql
    # only_missing already describes the outstanding work, so a failing row
    # behind the cursor must keep counting as remaining.
    assert "products.id > " not in sql
    assert "products.store =" in sql
    assert "products.embedding IS NULL" in sql


def test_reindex_remaining_count_in_a_full_sweep_is_bounded_by_the_cursor():
    sql = str(
        build_reindex_remaining_stmt(after_id="gmo:100").compile(
            dialect=postgresql.dialect()
        )
    )

    assert "products.id > " in sql
    assert "LIMIT" not in sql
