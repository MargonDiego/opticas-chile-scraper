import pytest
from src.models import StoreEnum, CategoryEnum, Product, PriceSnapshot
from src.scrapers.base import clean_clp_price, detect_category


def test_clean_clp_price():
    assert clean_clp_price("$ 149.990") == 149990
    assert clean_clp_price("149.990 CLP") == 149990
    assert clean_clp_price("$99.900") == 99900
    assert clean_clp_price(85000) == 85000
    assert clean_clp_price(None) is None
    assert clean_clp_price("") is None


def test_detect_category():
    assert detect_category("Lentes de Sol Ray-Ban Aviator") == CategoryEnum.SOL.value
    assert detect_category("Armazón Óptico Vogue") == CategoryEnum.OPTICOS.value
    assert detect_category("Lentes de Contacto Acuvue Oasys") == CategoryEnum.CONTACTO.value
    assert detect_category("Estuche rígido para anteojos") == CategoryEnum.ACCESORIOS.value


def test_product_model_initialization():
    prod = Product(
        id="gmo:12345",
        store=StoreEnum.GMO.value,
        store_product_id="12345",
        brand="Ray-Ban",
        model_name="Aviator Classic",
        category=CategoryEnum.SOL.value,
        url="https://www.gmo.cl/ray-ban-aviator",
    )
    assert prod.id == "gmo:12345"
    assert prod.store == "gmo"
    assert prod.brand == "Ray-Ban"
