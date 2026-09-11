import difflib

from src.models import ProductRead

OPTICAL_BRAND_ALIASES = {
    "oakely": "oakley", "aokley": "oakley", "okley": "oakley", "oakly": "oakley",
    "rayban": "ray-ban", "ray ban": "ray-ban", "reiban": "ray-ban", "reban": "ray-ban",
    "arnet": "arnette", "arnett": "arnette",
    "voge": "vogue", "vog": "vogue",
    "karun": "karün", "carun": "karün",
    "polaroide": "polaroid",
    "polarizdo": "polarizado", "polarizada": "polarizado", "polarizados": "polarizados",
    "dorad": "dorado", "dorada": "dorado", "platead": "plateado", "plateada": "plateado",
    "armazon": "armazón", "armazones": "armazón", "marcos": "marco",
}


def expand_and_correct_query(query: str, all_brands: list[str]) -> tuple[str, list[str]]:
    """Google-like query spelling correction and token expansion."""
    raw_tokens = [t.strip().lower() for t in query.split() if t.strip()]
    expanded = set(raw_tokens)
    corrected_words = []

    for t in raw_tokens:
        corrected = t
        if t in OPTICAL_BRAND_ALIASES:
            corrected = OPTICAL_BRAND_ALIASES[t]
            expanded.add(corrected)
        elif all_brands:
            matches = difflib.get_close_matches(t.capitalize(), all_brands, n=1, cutoff=0.75)
            if matches:
                corrected = matches[0].lower()
                expanded.add(corrected)
        corrected_words.append(corrected)

    clean_corrected_query = " ".join(corrected_words)
    return clean_corrected_query, list(expanded)


def lexical_score(search_tokens: list[str], mapped: ProductRead) -> float:
    """Score a product's textual relevance against pre-expanded search tokens.

    Shared by the keyword search (/api/products) and the hybrid semantic
    search (/api/products/search/semantic) endpoints, which previously
    duplicated this exact scoring logic.
    """
    if not search_tokens:
        return 0.0

    m_name = (mapped.model_name or "").lower()
    m_brand = (mapped.brand or "").lower()
    m_desc = (mapped.description or "").lower()
    m_cat = (mapped.category or "").lower()

    score = 0.0
    for tok in search_tokens:
        if tok == m_brand or tok in m_brand:
            score += 100.0
        elif tok in m_name:
            score += 60.0
        elif tok in m_cat:
            score += 30.0
        elif tok in m_desc:
            score += 15.0
        elif len(tok) >= 4 and difflib.SequenceMatcher(None, tok, m_brand).ratio() >= 0.75:
            score += 80.0

    return score


def apply_deal_filter(deal: str | None, mapped: ProductRead, price: float) -> bool:
    """Return True if the product should be kept under the given deal filter."""
    if deal == "disc-40":
        if not mapped.current_price_discount or not mapped.current_price_normal:
            return False
        pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
        return pct >= 40.0
    if deal == "disc-20":
        if not mapped.current_price_discount or not mapped.current_price_normal:
            return False
        pct = ((mapped.current_price_normal - mapped.current_price_discount) / mapped.current_price_normal) * 100.0
        return pct >= 20.0
    if deal == "under-50k":
        return 0 < price <= 50000
    if deal == "under-100k":
        return 0 < price <= 100000
    return True
