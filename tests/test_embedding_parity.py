"""Parity between the scrape path and the re-index path.

Both call sites feed the same ``build_embedding_text`` function, and both write
the same pgvector column. If either passes different field values for the same
stored row (or stops passing a field), the two writers diverge and search
quality silently depends on which one ran last. This module asserts the
invariant directly on the arguments each call site passes.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

import src.main as main_module
from src.config import settings
from src.database import async_session_factory
from src.models import Product
from src.scrapers.base import ScrapedItem
from src.scrapers.registry import SCRAPER_REGISTRY, execute_scrape_for_store
from src.services.ollama import ollama_service

ADMIN_KEY = "test-admin-key"
REINDEX_ENDPOINT = "/api/admin/embeddings/reindex"
VECTOR = [0.03] * 8
FIELD_SET = {"brand", "model_name", "category", "store", "description"}


class _FakeScraper:
    """Minimal adapter: one item, no network, no parsing."""

    items: list = []

    def __init__(self) -> None:
        pass

    async def scrape_catalog(self, max_pages=None):
        for item in self.items:
            yield item


def _item(description) -> ScrapedItem:
    return ScrapedItem(
        store="gmo",
        store_product_id="1",
        brand="Polaroid",
        model_name="Kids 0100",
        category="opticos",
        url="https://example.com/gmo/1",
        price_normal=49990,
        description=description,
    )


async def _seed_product(description) -> None:
    async with async_session_factory() as session:
        session.add(
            Product(
                id="gmo:1",
                store="gmo",
                store_product_id="1",
                brand="Polaroid",
                model_name="Kids 0100",
                category="opticos",
                url="https://example.com/gmo/1",
                description=description,
            )
        )
        await session.commit()


async def _stored_product() -> Product:
    async with async_session_factory() as session:
        result = await session.execute(select(Product).where(Product.id == "gmo:1"))
        return result.scalar_one()


@pytest.fixture
def spies(monkeypatch):
    """Record the kwargs each call site passes to ``build_embedding_text``."""
    calls = {"scraper": [], "reindex": []}
    real = main_module.build_embedding_text

    def _scraper_spy(**kwargs):
        calls["scraper"].append(kwargs)
        return real(**kwargs)

    def _reindex_spy(**kwargs):
        calls["reindex"].append(kwargs)
        return real(**kwargs)

    # Both call sites import the name into their own namespace.
    import src.scrapers.registry as registry_module

    monkeypatch.setattr(registry_module, "build_embedding_text", _scraper_spy)
    monkeypatch.setattr(main_module, "build_embedding_text", _reindex_spy)
    return calls


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    async def _fake_embedding(_text):
        return list(VECTOR)

    monkeypatch.setattr(ollama_service, "get_embedding", _fake_embedding)


@pytest.fixture
def fake_scraper(monkeypatch):
    class _Scraper(_FakeScraper):
        items = []

    monkeypatch.setitem(SCRAPER_REGISTRY, "gmo", _Scraper)
    return _Scraper


@pytest.fixture(autouse=True)
def admin_key(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)


async def _run_both_paths(spies, fake_scraper, description) -> None:
    fake_scraper.items = [_item(description)]
    await execute_scrape_for_store("gmo")

    async with AsyncClient(
        transport=ASGITransport(app=main_module.app), base_url="http://test"
    ) as client:
        response = await client.post(
            REINDEX_ENDPOINT, headers={"X-API-Key": ADMIN_KEY}
        )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_empty_incoming_description_keeps_the_stored_value(spies, fake_scraper):
    await _seed_product("Armazón infantil con lentes polarizados.")

    await _run_both_paths(spies, fake_scraper, None)

    # Empty scrape output must not erase stored catalog copy...
    assert (await _stored_product()).description == "Armazón infantil con lentes polarizados."
    # ...and the embedding was composed from the value that got persisted.
    assert spies["scraper"][-1]["description"] == "Armazón infantil con lentes polarizados."
    assert spies["scraper"][-1] == spies["reindex"][-1]


@pytest.mark.asyncio
async def test_new_description_is_persisted_before_the_reindex_reads_it(spies, fake_scraper):
    await _seed_product("Texto viejo.")

    await _run_both_paths(spies, fake_scraper, "Lentes polarizados para exteriores.")

    assert (await _stored_product()).description == "Lentes polarizados para exteriores."
    assert spies["scraper"][-1]["description"] == "Lentes polarizados para exteriores."
    assert spies["scraper"][-1] == spies["reindex"][-1]


@pytest.mark.asyncio
async def test_both_call_sites_pass_the_same_field_set(spies, fake_scraper):
    await _seed_product("Armazón infantil.")

    await _run_both_paths(spies, fake_scraper, "Armazón infantil.")

    assert set(spies["scraper"][-1]) == FIELD_SET
    assert set(spies["reindex"][-1]) == FIELD_SET
