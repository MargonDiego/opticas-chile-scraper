import pytest
from src.scrapers.gmo import GMOScraper
from src.scrapers.place_vendome import PlaceVendomeScraper
from src.scrapers.rotter_krauss import RotterKraussScraper
from src.scrapers.registry import get_available_stores


def test_scraper_registry():
    stores = get_available_stores()
    assert "gmo" in stores
    assert "ryk" in stores
    assert "schilling" in stores
    assert "place_vendome" in stores
    assert "econopticas" in stores


def test_gmo_parse_shopify_product():
    scraper = GMOScraper()
    mock_shopify = {
        "id": 998877,
        "title": "Lentes de Sol Ray-Ban Justin",
        "vendor": "Ray-Ban",
        "handle": "ray-ban-justin",
        "product_type": "Sol",
        "images": [{"src": "https://gmo.cl/cdn/123.jpg"}],
        "variants": [
            {
                "price": "119990",
                "compare_at_price": "149990",
                "available": True,
            }
        ],
    }

    item = scraper._parse_shopify(mock_shopify)
    assert item is not None
    assert item.store == "gmo"
    assert item.brand == "Ray-Ban"
    assert item.price_normal == 149990
    assert item.price_discount == 119990
    assert item.is_in_stock is True
    assert item.category == "sol"


def test_place_vendome_parse_shopify_product():
    scraper = PlaceVendomeScraper()
    mock_shopify = {
        "id": 112233,
        "title": "Armazón Óptico Oakley Holbrook",
        "vendor": "Oakley",
        "handle": "oakley-holbrook",
        "product_type": "Ópticos",
        "images": [{"src": "https://cdn.shopify.com/123.jpg"}],
        "variants": [
            {
                "price": "129990",
                "compare_at_price": "159990",
                "available": True,
            }
        ],
    }

    item = scraper._parse_shopify(mock_shopify)
    assert item is not None
    assert item.store == "place_vendome"
    assert item.brand == "Oakley"
    assert item.price_normal == 159990
    assert item.price_discount == 129990
    assert item.is_in_stock is True