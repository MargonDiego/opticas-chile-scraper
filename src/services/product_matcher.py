import re

from src.models import Product, ProductRead

CANONICAL_MODEL_REGEX = re.compile(
    r'\b(?:0?([a-zA-Z]{1,4})\s*[-_]?\s*(\d{3,5}[a-zA-Z]{0,3}))\b',
    re.IGNORECASE,
)

EYEWEAR_STOPWORDS = {
    "lentes", "lente", "anteojos", "anteojo", "gafas", "gafa", "armazon", "armazón", "armazones",
    "marcos", "marco", "de", "sol", "opticos", "optico", "ópticos", "óptico", "contacto",
    "caja", "pack", "unidades", "unidad", "uds", "con", "para", "hombre", "mujer", "unisex",
    "polarizado", "polarizada", "polarizados", "clipon", "clip-on", "graduable", "lentesplus",
    "gmo", "ryk", "schilling", "econopticas", "opv"
}


def extract_canonical_key(prod: ProductRead | Product) -> tuple[str, str]:
    """Derive a cross-store identity key so the same model can be matched
    across different optical chains for price comparison."""
    brand = (prod.brand or "").strip().lower()
    if "ray" in brand and "ban" in brand:
        brand = "ray-ban"
    elif "oakley" in brand:
        brand = "oakley"
    elif "karun" in brand or "karün" in brand:
        brand = "karün"
    elif "vogue" in brand:
        brand = "vogue"
    elif "arnette" in brand:
        brand = "arnette"
    elif "acuvue" in brand:
        brand = "acuvue"
    elif "alcon" in brand:
        brand = "alcon"
    elif "bausch" in brand or "lomb" in brand:
        brand = "bausch-lomb"
    elif "coopervision" in brand:
        brand = "coopervision"

    model_text = f"{prod.model_name or ''} {getattr(prod, 'store_product_id', '') or ''}".strip()
    match = CANONICAL_MODEL_REGEX.search(model_text)
    if match:
        prefix = match.group(1).upper()
        if prefix.startswith("0") and len(prefix) > 1:
            prefix = prefix[1:]
        code_num = match.group(2).upper()
        clean_code = f"{prefix}{code_num}"
        return f"{brand}:{clean_code.lower()}", clean_code

    raw_tokens = re.findall(r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+', model_text.lower())
    clean_tokens = [t for t in raw_tokens if t not in EYEWEAR_STOPWORDS and len(t) > 1]
    if clean_tokens:
        key_tokens = clean_tokens[:3]
        clean_line = " ".join(key_tokens).title()
        return f"{brand}:{'_'.join(key_tokens)}", clean_line

    fallback = (getattr(prod, "store_product_id", "") or prod.id).lower()
    return f"{brand}:{fallback}", prod.model_name or ""
