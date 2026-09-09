import pytest
from src.scrapers.gmo import GMOScraper
from src.scrapers.place_vendome import PlaceVendomeScraper
from src.scrapers.karun import KarunScraper
from src.scrapers.registry import get_available_stores


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