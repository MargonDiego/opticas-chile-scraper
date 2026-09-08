import pytest
from src.scrapers.gmo import GMOScraper
from src.scrapers.rotter_krauss import RotterKraussScraper
from src.scrapers.registry import get_available_stores


def test_scraper_registry():
    stores = get_available_stores()
    assert "gmo" in stores
    assert "ryk" in stores
    assert "schilling" in stores
    assert "place_vendome" in stores
    assert "econopticas" in stores


def test_gmo_parse_vtex_product():
    scraper = GMOScraper()
    mock_prod = {
        "productId": "998877",
        "productName": "Lentes de Sol Ray-Ban Justin",
        "brand": "Ray-Ban",
        "link": "/ray-ban-justin/p",
        "categories": ["/Lentes de Sol/"],
        "items": [
            {
                "images": [{"imageUrl": "https://gmo.vteximg.com.br/123.jpg"}],
                "sellers": [
                    {
                        "commertialOffer": {
                            "ListPrice": 149990,
                            "Price": 119990,
                            "AvailableQuantity": 5,
                        }
                    }
                ],
            }
        ],
    }

    item = scraper._parse_vtex_product(mock_prod)
    assert item is not None
    assert item.store == "gmo"
    assert item.store_product_id == "998877"
    assert item.brand == "Ray-Ban"
    assert item.price_normal == 149990
    assert item.price_discount == 119990
    assert item.is_in_stock is True
    assert item.category == "sol"


def test_rotter_krauss_parse_shopify_product():
    scraper = RotterKraussScraper()
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

    item = scraper._parse_shopify_product(mock_shopify)
    assert item is not None
    assert item.store == "ryk"
    assert item.brand == "Oakley"
    assert item.price_normal == 159990
    assert item.price_discount == 129990
    assert item.is_in_stock is True
