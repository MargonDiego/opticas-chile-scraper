import difflib
import re
from typing import Optional, Tuple

OPTICAL_STOP_WORDS = {
    "lentes", "anteojos", "gafas", "para", "busca", "buscar", "quiero",
    "necesito", "precio", "chile", "como", "unos", "unas", "del", "las",
    "los", "con", "sin", "que", "una", "uno", "por", "favor", "recomienda",
    "recomiendame", "dame", "cual", "cuales", "mejores", "mejor", "buenos",
    "bueno", "buenas", "buena", "hay", "tienen", "algo", "tipo", "estilo", "marca", "marcas",
    "pero", "mas", "más", "menos", "de", "en", "el", "la", "los", "las",
    "pa", "para", "piola", "weno", "buenisimo", "bakan", "bacanes", "onda", "unos",
    "lucas", "lucas?", "luca", "mil", "pesos", "hasta", "máximo", "maximo", "menos", "presupuesto"
}

BUDGET_CHEAP_KEYWORDS = {
    "barato", "baratos", "barata", "baratas", "barto", "bartos", "baratito", "baratitos",
    "economico", "economicos", "economica", "economicas", "oferta", "ofertas", "descuento",
    "descuentos", "rebaja", "rebajas", "liquidacion", "liquidaciones", "ganga", "gangas",
    "accesible", "accesibles", "ahorro", "barat"
}

BUDGET_EXPENSIVE_KEYWORDS = {
    "caro", "caros", "cara", "caras", "lujo", "premium", "alta gama", "top", "exclusivo", "exclusivos"
}

INTENT_CATEGORY_MAP = {
    "trekking": "sol",
    "senderismo": "sol",
    "montaña": "sol",
    "playa": "sol",
    "deporte": "sol",
    "deportivos": "sol",
    "ciclismo": "sol",
    "running": "sol",
    "sol": "sol",
    "polarizados": "sol",
    "polarizado": "sol",
    "aviador": "sol",
    "aviator": "sol",
    "armazon": "opticos",
    "armazones": "opticos",
    "marcos": "opticos",
    "marco": "opticos",
    "computador": "opticos",
    "pantalla": "opticos",
    "pantallas": "opticos",
    "oficina": "opticos",
    "pega": "opticos",
    "trabajo": "opticos",
    "laburo": "opticos",
    "filtro azul": "opticos",
    "blue defense": "opticos",
    "receta": "opticos",
    "lectura": "opticos",
    "contacto": "contacto",
    "acuvue": "contacto",
    "biofinity": "contacto",
    "astigmatismo": "contacto",
    "miopia": "contacto",
    "toricos": "contacto",
    "diarios": "contacto",
    "mensuales": "contacto",
}

INTENT_SYNONYMS = {
    "trekking": ["outdoor", "polarizad", "karun", "oakley", "arnette", "deport", "sol"],
    "senderismo": ["outdoor", "polarizad", "karun", "oakley", "sol"],
    "montaña": ["outdoor", "polarizad", "karun", "oakley", "sol"],
    "deporte": ["oakley", "arnette", "polarizad", "deport", "sol"],
    "deportivos": ["oakley", "arnette", "polarizad", "deport", "sol"],
    "ciclismo": ["oakley", "arnette", "polarizad", "sol"],
    "running": ["oakley", "polarizad", "arnette", "sol"],
    "computador": ["blue", "azul", "filtro", "optico"],
    "pantalla": ["blue", "azul", "filtro", "optico"],
    "pantallas": ["blue", "azul", "filtro", "optico"],
    "pega": ["optico", "azul", "blue", "armazon"],
    "trabajo": ["optico", "azul", "blue", "armazon"],
    "polarizados": ["polarizad", "polarizado"],
    "polarizado": ["polarizad", "polarizado"],
    "contacto": ["contacto", "acuvue", "biofinity", "soflens", "dailies"],
    "rayban": ["ray-ban", "ray ban", "aviator", "wayfarer"],
    "oakley": ["oakley", "deport", "polarizad"],
    "karun": ["karun", "sustentable", "polarizad"],
    "ecologicos": ["karun", "sustentable"],
    "ecologicas": ["karun", "sustentable"],
    "sustentables": ["karun", "sustentable"],
    "sustentable": ["karun", "sustentable"],
    "redondos": ["round", "redondo", "circular"],
    "cuadrados": ["square", "cuadrado", "rectangular"],
    "negros": ["negro", "black"],
    "dorados": ["dorado", "gold"],
    "carey": ["havana", "carey", "tortoise"],
    "havana": ["havana", "carey"],
    "transparentes": ["transparente", "clear", "cristal"],
}

STORE_ALIASES = {
    "gmo": "gmo",
    "opticas gmo": "gmo",
    "ópticas gmo": "gmo",
    "place vendome": "place_vendome",
    "place vendôme": "place_vendome",
    "opv": "place_vendome",
    "rotter": "ryk",
    "rotter & krauss": "ryk",
    "rotter y krauss": "ryk",
    "ryk": "ryk",
    "schilling": "schilling",
    "opticas schilling": "schilling",
    "ópticas schilling": "schilling",
    "econopticas": "econopticas",
    "econópticas": "econopticas",
    "karun": "karun",
    "karün": "karun",
    "lentesplus": "lentesplus",
}

BRAND_ALIASES = {
    "rayban": "Ray-Ban",
    "ray-ban": "Ray-Ban",
    "ray ban": "Ray-Ban",
    "oakley": "Oakley",
    "vogue": "Vogue",
    "karun": "Karün",
    "karün": "Karün",
    "acuvue": "Acuvue",
    "armani exchange": "Armani Exchange",
    "armani": "Armani",
    "michael kors": "Michael Kors",
    "alcon": "Alcon",
    "arnette": "Arnette",
    "burberry": "Burberry",
    "montini": "Montini",
    "biofinity": "Biofinity",
    "tecnol": "Tecnol",
    "ralph": "Ralph",
    "prada": "Prada",
    "gucci": "Gucci",
    "versace": "Versace",
    "soflens": "SofLens",
    "dailies": "Dailies",
    "carrera": "Carrera",
    "police": "Police",
    "hugo boss": "Boss",
    "boss": "Boss",
}


def detect_store(text: str) -> Optional[str]:
    t_lower = text.lower()
    for alias, store_id in sorted(STORE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", t_lower):
            return store_id
    return None


def detect_brand(text: str) -> Optional[str]:
    t_lower = text.lower()
    # 1. Direct match
    for alias, brand_name in sorted(BRAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in t_lower:
            return brand_name
    # 2. Fuzzy match word by word for common typos (e.g. 'rayan' -> 'Ray-Ban')
    words = [w.strip(".,;:!?\"'()") for w in t_lower.split()]
    for w in words:
        if len(w) >= 4:
            matches = difflib.get_close_matches(w, list(BRAND_ALIASES.keys()), n=1, cutoff=0.72)
            if matches:
                return BRAND_ALIASES[matches[0]]
    return None


def parse_amount(raw: str) -> Optional[int]:
    if not raw:
        return None
    raw_clean = raw.lower().replace("$", "").replace(".", "").replace(",", "").strip()
    if "lucas" in raw_clean or "luca" in raw_clean or raw_clean.endswith("k"):
        num_str = re.sub(r"[^\d]", "", raw_clean)
        if num_str:
            return int(num_str) * 1000
    num_str = re.sub(r"[^\d]", "", raw_clean)
    if not num_str:
        return None
    val = int(num_str)
    if val < 500:
        val *= 1000
    return val


def extract_budget_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract (min_price, max_price) in CLP from natural Spanish queries."""
    text_lower = text.lower()

    # 1. Range: 'entre los X y los Y', 'entre X y Y', 'de X a Y', 'desde X hasta Y'
    range_patterns = [
        r"(?:entre|rango\s+de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)\s+(?:y|e|a|-)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)",
        r"(?:desde|de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)\s+(?:hasta|a|-)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)",
    ]
    for pat in range_patterns:
        m = re.search(pat, text_lower)
        if m:
            min_val = parse_amount(m.group(1))
            max_val = parse_amount(m.group(2))
            if min_val and max_val:
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                return min_val, max_val

    # 2. Minimum only: 'sobre X', 'mas de X', 'mayor a X', 'desde X'
    min_pattern = r"(?:sobre|m[aá]s\s+de|mayor(?:es)?\s+a|desde|m[ií]nimo|m[ií]nima|a\s+partir\s+de)\s+(?:los\s+|las\s+)?\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)"
    m_min = re.search(min_pattern, text_lower)
    min_val = parse_amount(m_min.group(1)) if m_min else None

    # 3. Maximum only: 'menos de X', 'bajo los X', 'bajo X', 'hasta X', 'maximo X'
    max_pattern = r"(?:menos\s+de|bajo\s+(?:los\s+|las\s+)?|menor(?:es)?\s+a|hasta\s+(?:los\s+|las\s+)?|m[aá]ximo\s+(?:de\s+)?|tope\s+(?:de\s+)?|presupuesto\s+(?:de\s+)?)\s*\$?([0-9.,k]+(?:\s*lucas?|\s*mil)?)"
    m_max = re.search(max_pattern, text_lower)
    max_val = parse_amount(m_max.group(1)) if m_max else None

    if min_val or max_val:
        return min_val, max_val

    # 4. Standalone lucas/k
    m_lucas = re.search(r"(\d+)\s*(?:lucas?|k\b)", text_lower)
    if m_lucas:
        val = int(m_lucas.group(1)) * 1000
        return None, val

    return None, None


def detect_category(text: str) -> Optional[str]:
    """Detect optical product category from multi-word phrases and domain keywords."""
    t = text.lower()
    # 1. Contact lenses
    if any(k in t for k in ["contacto", "lentilla", "lentillas", "biofinity", "acuvue", "astigmatismo", "miopia", "toricos", "diarios", "mensuales", "soflens", "dailies"]):
        return "contacto"
    # 2. Sunglasses
    if any(k in t for k in ["lentes de sol", "anteojos de sol", "gafas de sol", "gafas solares", "sol", "polarizado", "polarizados", "polarized", "aviador", "aviator", "trekking", "senderismo", "playa", "ciclismo", "running"]):
        return "sol"
    # 3. Optical frames
    if any(k in t for k in ["lentes opticos", "lentes ópticos", "anteojos opticos", "anteojos ópticos", "armazon", "armazones", "marco", "marcos", "computador", "pantalla", "filtro azul", "blue defense", "receta", "lectura", "descanso", "pega", "trabajo", "laburo"]):
        return "opticos"
    return None
