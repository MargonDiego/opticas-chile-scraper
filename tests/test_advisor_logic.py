import pytest
from src.services.advisor_nlu import extract_budget_range as _extract_budget_range


@pytest.mark.parametrize(
    "query,expected_min,expected_max",
    [
        ("lentes de sol con precio bajo los 100000 con stock", None, 100_000),
        ("quiero lentes opticos bajo 50000", None, 50_000),
        ("armazones menos de 80 lucas", None, 80_000),
        ("lentes de contacto hasta 30k", None, 30_000),
        ("gafas de sol maximo $120.000", None, 120_000),
        ("presupuesto de 45 mil", None, 45_000),
        ("lentes de sol bajo los $60.000 con descuento", None, 60_000),
        ("armazones sobre los 20000", 20_000, None),
        ("lentes entre 30000 y 80000", 30_000, 80_000),
        ("sin ninguna mención de precio", None, None),
    ],
)
def test_extract_budget_range(query, expected_min, expected_max):
    min_val, max_val = _extract_budget_range(query)
    assert min_val == expected_min
    assert max_val == expected_max
