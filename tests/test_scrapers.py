import pytest
from bs4 import BeautifulSoup
from src.scrapers.gmo import GMOScraper
from src.scrapers.place_vendome import PlaceVendomeScraper
from src.scrapers.karun import KarunScraper
from src.scrapers.rotter_krauss import RotterKraussScraper
from src.scrapers.schilling import SchillingScraper
from src.scrapers.econopticas import EconopticasScraper
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