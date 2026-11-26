import pytest
from bs4 import BeautifulSoup
from src.config import settings
from src.models import JobStatusEnum
from src.scrapers import registry as scraper_registry
from src import scheduler as scraper_scheduler
from src.scrapers import base as base_module
from src.scrapers.base import BaseOpticalScraper
from src.scrapers.gmo import GMOScraper
from src.scrapers.place_vendome import PlaceVendomeScraper
from src.scrapers.karun import KarunScraper
from src.scrapers.rotter_krauss import RotterKraussScraper
from src.scrapers.schilling import SchillingScraper
from src.scrapers.econopticas import EconopticasScraper
from src.scrapers.registry import execute_scrape_for_store, get_available_stores


def test_scraper_registry():
    stores = get_available_stores()
    assert "gmo" in stores
    assert "ryk" in stores
    assert "schilling" in stores
    assert "place_vendome" in stores
    assert "econopticas" in stores
    assert "karun" in stores
    assert "lentesplus" in stores


def test_karun_parse_shopify_product():
    scraper = KarunScraper()
    mock_shopify = {
        "id": 554433,
        "title": "Anteojos de Sol Karün Yuco",
        "vendor": "Karün",
        "handle": "karun-yuco",
        "product_type": "Sol",
        "images": [{"src": "https://karun.cl/cdn/yuco.jpg"}],
        "variants": [
            {
                "price": "99000",
                "compare_at_price": "119000",
                "available": True,
            }
        ],
    }

    item = scraper._parse_shopify(mock_shopify)
    assert item is not None
    assert item.store == "karun"
    assert item.brand == "Karün"
    assert item.price_normal == 119000
    assert item.price_discount == 99000
    assert item.is_in_stock is True


def test_rotter_krauss_parse_tile():
    """Smoke test for the SFCC-style tile markup RyK's category pages use."""
    html = """
    <div class="product" data-pid="12345">
        <a class="pdp-link" href="/ray-ban-aviador-clasico-12345.html">
            <img class="tile-image" src="//cdn.ryk.cl/img/rayban.jpg" alt="Ray-Ban Aviador Clásico">
        </a>
        <div class="price">
            <span class="strike-through">$150.000</span>
            <span class="sales">$99.000</span>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(".product[data-pid]")
    assert card is not None

    scraper = RotterKraussScraper()
    item = scraper._parse_tile(card, "/anteojos-de-sol")

    assert item is not None
    assert item.store == "ryk"
    assert item.store_product_id == "12345"
    assert item.brand == "Ray-Ban"
    assert item.price_normal == 150000
    assert item.price_discount == 99000
    assert item.url.endswith("/ray-ban-aviador-clasico-12345.html")


def test_schilling_parse_card():
    """Smoke test for Schilling's Magento 2 product-item-info markup."""
    html = """
    <div class="product-item-info">
        <a class="product-item-photo" href="/marco-oakley-holbrook.html"
           onclick="dataLayer.push({'item_brand':'Oakley'})">
            <img class="product-image-photo" src="//cdn.schilling.cl/img/oakley.jpg" alt="Marco Oakley Holbrook">
        </a>
        <a class="product-item-link" href="/marco-oakley-holbrook.html">Marco Oakley Holbrook</a>
        <div class="price-box">
            <span class="old-price"><span class="price">$120.000</span></span>
            <span class="special-price"><span class="price">$89.000</span></span>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(".product-item-info")
    assert card is not None

    scraper = SchillingScraper()
    item = scraper._parse_card(card, "/lentes-opticos.html")

    assert item is not None
    assert item.store == "schilling"
    assert item.brand == "Oakley"
    assert item.price_normal == 120000
    assert item.price_discount == 89000
    assert item.store_product_id == "marco-oakley-holbrook"


def test_econopticas_parse_tile():
    """Smoke test for Econopticas' Magento 2 product-item-info markup."""
    html = """
    <div class="product-item-info">
        <a class="product-item-photo" href="/lentes-vogue-vo5228.html">
            <img class="product-image-photo" src="//cdn.econopticas.cl/img/vogue.jpg" alt="Lentes Vogue VO5228">
        </a>
        <div class="product-link"><a href="/lentes-vogue-vo5228.html">Lentes Vogue VO5228</a></div>
        <div class="product-brand"><a>Vogue</a></div>
        <div class="price-box">
            <span class="old-price"><span class="price">$95.000</span></span>
            <span class="special-price"><span class="price">$65.000</span></span>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    tile = soup.select_one(".product-item-info, .product-item")
    assert tile is not None

    scraper = EconopticasScraper()
    item = scraper._parse_tile(tile, "/anteojos-opticos")

    assert item is not None
    assert item.store == "econopticas"
    assert item.brand == "Vogue"
    assert item.price_normal == 95000
    assert item.price_discount == 65000


def test_place_vendome_parse_vtex():
    """Smoke test for the VTEX fallback catalog Place Vendome falls back to."""
    mock_vtex_product = {
        "productId": "778899",
        "productName": "Ray-Ban Wayfarer Clásico",
        "brand": "Ray-Ban",
        "link": "/ray-ban-wayfarer-clasico/p",
        "items": [
            {
                "sellers": [
                    {
                        "commertialOffer": {
                            "Price": 89000,
                            "ListPrice": 120000,
                            "AvailableQuantity": 5,
                        }
                    }
                ],
                "images": [{"imageUrl": "https://vtexassets.opv.cl/img/wayfarer.jpg"}],
            }
        ],
    }

    scraper = PlaceVendomeScraper()
    item = scraper._parse_vtex(mock_vtex_product)

    assert item is not None
    assert item.store == "place_vendome"
    assert item.store_product_id == "778899"
    assert item.price_normal == 120000
    assert item.price_discount == 89000
    assert item.is_in_stock is True


class _EmptyScraper(BaseOpticalScraper):
    """Scraper that completes normally but yields nothing."""

    def __init__(self):
        super().__init__(store_name="test_empty", base_url="https://example.invalid")

    async def scrape_catalog(self, max_pages=None):
        for _ in ():
            yield _


async def test_execute_scrape_marks_failed_when_zero_items(monkeypatch):
    monkeypatch.setitem(scraper_registry.SCRAPER_REGISTRY, "test_empty", _EmptyScraper)

    job = await execute_scrape_for_store("test_empty", max_pages=1)

    assert job.status == JobStatusEnum.FAILED.value
    assert job.error_message == "Scraper returned 0 items"
    assert job.items_scraped == 0
    assert job.completed_at is not None


# --- curl_cffi impersonated fetch helper -------------------------------------


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncSession:
    """Stands in for curl_cffi.requests.AsyncSession in unit tests."""

    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, params=None):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _patch_session(monkeypatch, responses):
    monkeypatch.setattr(
        base_module,
        "AsyncSession",
        lambda **kwargs: _FakeAsyncSession(responses),
    )
    # Retries would otherwise really sleep between attempts.
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(base_module.asyncio, "sleep", _no_sleep)
    monkeypatch.setattr(settings, "SCRAPER_RETRY_ATTEMPTS", 3)


async def test_fetch_json_impersonated_returns_payload(monkeypatch):
    _patch_session(monkeypatch, [_FakeResponse(200, {"products": [{"id": 1}]})])

    data = await GMOScraper().fetch_json_impersonated("https://gmo.cl/products.json")

    assert data == {"products": [{"id": 1}]}


async def test_fetch_json_impersonated_retries_429_then_gives_up(monkeypatch):
    _patch_session(
        monkeypatch,
        [_FakeResponse(429), _FakeResponse(429), _FakeResponse(429)],
    )

    data = await GMOScraper().fetch_json_impersonated("https://gmo.cl/products.json")

    assert data is None


async def test_fetch_json_impersonated_retries_transport_error(monkeypatch):
    _patch_session(
        monkeypatch,
        [RuntimeError("connection reset"), _FakeResponse(200, {"products": []})],
    )

    data = await GMOScraper().fetch_json_impersonated("https://gmo.cl/products.json")

    assert data == {"products": []}


async def test_fetch_json_impersonated_returns_none_on_permanent_status(monkeypatch):
    _patch_session(monkeypatch, [_FakeResponse(404)])

    data = await GMOScraper().fetch_json_impersonated("https://gmo.cl/products.json")

    assert data is None


async def test_gmo_scraper_handles_fetch_failure_without_raising(monkeypatch):
    async def _fail(_self, url, params=None):
        return None

    monkeypatch.setattr(GMOScraper, "fetch_json_impersonated", _fail)

    items = [item async for item in GMOScraper().scrape_catalog(max_pages=1)]

    assert items == []


async def test_gmo_scraper_yields_items_from_impersonated_fetch(monkeypatch):
    page_one = {
        "products": [
            {
                "id": 1,
                "title": "Ray-Ban Aviador",
                "vendor": "Ray-Ban",
                "handle": "ray-ban-aviador",
                "product_type": "Sol",
                "images": [],
                "variants": [{"price": "99000", "compare_at_price": None, "available": True}],
            }
        ]
    }

    async def _fetch(_self, url, params=None):
        return page_one if "page=1" in url else {"products": []}

    monkeypatch.setattr(GMOScraper, "fetch_json_impersonated", _fetch)

    items = [item async for item in GMOScraper().scrape_catalog(max_pages=1)]

    assert len(items) == 1
    assert items[0].store == "gmo"
    assert items[0].store_product_id == "1"


# --- scheduler cross-process lock -------------------------------------------


async def test_scheduled_scrape_lock_is_exclusive(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper_scheduler, "SCRAPE_LOCK_FILE", tmp_path / "scrape.lock")

    async with scraper_scheduler.scheduled_scrape_lock() as first:
        assert first is True
        async with scraper_scheduler.scheduled_scrape_lock() as second:
            assert second is False

    # Released on exit, so the next acquisition wins again.
    async with scraper_scheduler.scheduled_scrape_lock() as again:
        assert again is True


async def test_scheduled_scrape_skips_when_lock_is_held(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper_scheduler, "SCRAPE_LOCK_FILE", tmp_path / "scrape.lock")
    calls = []

    async def _record(store, max_pages=None):
        calls.append(store)

    monkeypatch.setattr(scraper_scheduler, "execute_scrape_for_store", _record)
    monkeypatch.setattr(scraper_scheduler, "get_available_stores", lambda: ["gmo"])

    async with scraper_scheduler.scheduled_scrape_lock() as held:
        assert held is True
        await scraper_scheduler.scheduled_scrape_all_stores()

    assert calls == []


async def test_scheduled_scrape_runs_when_lock_is_free(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper_scheduler, "SCRAPE_LOCK_FILE", tmp_path / "scrape.lock")
    calls = []

    async def _record(store, max_pages=None):
        calls.append(store)

    monkeypatch.setattr(scraper_scheduler, "execute_scrape_for_store", _record)
    monkeypatch.setattr(scraper_scheduler, "get_available_stores", lambda: ["gmo", "karun"])

    await scraper_scheduler.scheduled_scrape_all_stores()

    assert calls == ["gmo", "karun"]


async def test_stale_lock_file_is_stolen(monkeypatch, tmp_path):
    lock_file = tmp_path / "scrape.lock"
    monkeypatch.setattr(scraper_scheduler, "SCRAPE_LOCK_FILE", lock_file)
    lock_file.write_text("999")
    # Age the lock file past the staleness window.
    import os

    old = lock_file.stat().st_mtime - scraper_scheduler._SCRAPE_LOCK_STALE_SECONDS - 60
    os.utime(lock_file, (old, old))

    async with scraper_scheduler.scheduled_scrape_lock() as acquired:
        assert acquired is True