import logging
from typing import List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


def _clean_trailing_sentence(text: str) -> str:
    """Trim incomplete trailing sentence fragments to guarantee clean full stops."""
    trimmed = text.strip()
    if not trimmed:
        return trimmed
    if trimmed[-1] in ".!?":
        return trimmed
    last_punct = max(trimmed.rfind("."), trimmed.rfind("!"), trimmed.rfind("?"))
    if last_punct > 25:
        return trimmed[: last_punct + 1]
    return trimmed + "."


class OllamaService:
    """Client for Ollama LLM and Vector Embedding services with CPU optimizations."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.llm_model = settings.OLLAMA_LLM_MODEL
        self.timeout = httpx.Timeout(55.0, connect=2.0)
        self._working_url: Optional[str] = None

    def _get_candidate_urls(self) -> List[str]:
        if self._working_url:
            return [self._working_url]
        candidates = ["http://192.168.1.85:11434", self.base_url, "http://host.docker.internal:11434", "http://127.0.0.1:11434"]
        unique = []
        for c in candidates:
            if c not in unique:
                unique.append(c)
        return unique

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text vector embedding via Ollama."""
        if not text or not text.strip():
            return None

        payload = {
            "model": self.embed_model,
            "prompt": text.strip()[:150],
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/embeddings"
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=1.5)) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        self._working_url = base
                        data = res.json()
                        return data.get("embedding")
            except Exception as e:
                logger.debug(f"Ollama embedding attempt failed on {base}: {e}")
                continue

        return None

    async def ask_advisor(
        self,
        user_query: str,
        matched_products_context: str,
        is_cheap_intent: bool = False,
        budget_min: Optional[int] = None,
        budget_max: Optional[int] = None,
        detected_brand: Optional[str] = None,
        target_store: Optional[str] = None,
        requires_discount: bool = False,
    ) -> str:
        """Use Ollama LLM to synthesize optical product recommendations with guardrails."""
        constraints = []
        if target_store:
            constraints.append(f"Tienda solicitada: {target_store.upper()}.")
        if detected_brand:
            constraints.append(f"Marca solicitada: {detected_brand}.")
        if budget_min and budget_max:
            constraints.append(f"Rango de precio solicitado: entre ${budget_min:,} y ${budget_max:,} CLP.")
        elif budget_max:
            constraints.append(f"Presupuesto máximo: hasta ${budget_max:,} CLP.")
        elif budget_min:
            constraints.append(f"Presupuesto mínimo: desde ${budget_min:,} CLP.")

        if requires_discount:
            constraints.append("Filtro solicitado: Solo productos con descuento activo.")

        constraints_str = f"Restricciones activas: {' '.join(constraints)}\n" if constraints else ""

        focus_instruction = (
            "Destaca como opción principal el producto más conveniente de la lista (el primer producto del catálogo listado que cumple el presupuesto y filtros)."
            if (is_cheap_intent or budget_min or budget_max)
            else "Recomienda la opción más adecuada del catálogo y compara tiendas objetivamente."
        )

        prompt = (
            "Eres un Asesor Experto en Ópticas en Chile.\n"
            f"Consulta del usuario: '{user_query}'\n"
            f"{constraints_str}"
            "Catálogo de productos encontrados (ya filtrados y ordenados por conveniencia):\n"
            f"{matched_products_context}\n\n"
            "Reglas obligatorias:\n"
            f"1. {focus_instruction}\n"
            "2. Usa ÚNICAMENTE los nombres, marcas y precios exactos del catálogo listado arriba. NUNCA inventes productos ni alteres precios.\n"
            "3. Si mencionas el precio, escribe la cifra exacta en pesos chilenos ($ CLP).\n"
            "4. No des diagnósticos ni recetas médicas.\n"
            "5. Responde de forma concisa y directa en 2 oraciones completas y termina con punto final.\n\n"
            "Recomendación:"
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 90,
                "num_thread": 4,
                "temperature": 0.1,
                "top_k": 10,
            },
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/generate"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        self._working_url = base
                        raw_ans = res.json().get("response", "")
                        return _clean_trailing_sentence(raw_ans) if raw_ans else "Encontré las siguientes opciones destacadas en el catálogo:"
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


ollama_service = OllamaService()