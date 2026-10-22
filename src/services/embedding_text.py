"""Single source of truth for the text that gets embedded for a product.

Both the scrape/upsert path and the admin re-index endpoint must feed Ollama
the exact same text. Keeping the composition in one pure function means a
re-index produces vectors that match freshly scraped rows, and it makes the
builder unit-testable without a database session.

Changing anything in this module invalidates every stored embedding: run
``POST /api/admin/embeddings/reindex`` until ``done`` is true afterwards.
"""

import re
from typing import Optional

# nomic-embed-text accepts up to 8192 tokens (roughly 30k characters), so the
# old 150-character cap was discarding almost all product context and made
# descriptive queries ("armazon infantil") unable to match model names such as
# "Polaroid Kids (4-8 años)". 1200 characters holds a full product name plus a
# meaningful description slice (well under 1k tokens), which keeps embedding
# latency and vector payloads predictable while preserving that context.
MAX_EMBEDDING_TEXT_CHARS = 1200

# Mirrors the catalog exposed by GET /api/stores. Unknown ids fall back to the
# raw id so a new scraper is still embedded correctly before this map is
# updated.
STORE_DISPLAY_NAMES = {
    "gmo": "GMO Chile",
    "ryk": "Rotter & Krauss",
    "schilling": "Ópticas Schilling",
    "place_vendome": "Place Vendôme",
    "econopticas": "Econópticas",
    "karun": "Karün Chile",
    "lentesplus": "Lentesplus Chile",
}

_WHITESPACE_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def normalize_whitespace(value: Optional[str]) -> str:
    """Collapse every whitespace run to a single space and trim the edges."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value)).strip()


def strip_markup(value: Optional[str]) -> str:
    """Drop HTML tags from scraped descriptions before they reach a vector."""
    if not value:
        return ""
    return _HTML_TAG_RE.sub(" ", str(value))


def truncate_at_word_boundary(
    text: str, max_chars: int = MAX_EMBEDDING_TEXT_CHARS
) -> str:
    """Cut ``text`` to ``max_chars`` without leaving a dangling partial word.

    The cut is moved back to the last space so a token is never embedded in
    half. Text with no space in the window (a single very long word) is cut at
    the hard limit, because there is no word boundary to fall back to.
    """
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    boundary = cut.rfind(" ")
    if boundary > 0:
        cut = cut[:boundary]
    return cut.rstrip(" ,;:-")


def store_display_name(store: Optional[str]) -> str:
    """Resolve a store id to its human-readable name, falling back to the id."""
    normalized = normalize_whitespace(store)
    if not normalized:
        return ""
    return STORE_DISPLAY_NAMES.get(normalized.lower(), normalized)


def build_embedding_text(
    *,
    brand: Optional[str] = None,
    model_name: Optional[str] = None,
    category: Optional[str] = None,
    store: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Compose the canonical text embedded for one product.

    Order is brand, model name, category, store display name, description:
    brand and model carry the strongest matching signal, so they come first and
    survive truncation. Empty parts are dropped and whitespace is normalized,
    which keeps the output deterministic (same input -> byte-identical output).

    Returns an empty string when every part is empty; callers must then skip
    the embedding call instead of sending an empty prompt.
    """
    parts = [
        normalize_whitespace(brand),
        normalize_whitespace(model_name),
        normalize_whitespace(category),
        store_display_name(store),
        normalize_whitespace(strip_markup(description)),
    ]
    return truncate_at_word_boundary(" ".join(part for part in parts if part))
