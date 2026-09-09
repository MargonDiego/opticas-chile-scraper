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
        self.timeout = httpx.Timeout(25.0, connect=1.2)
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
                async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=1.0)) as client:
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
        self, user_query: str, matched_products_context: str, is_cheap_intent: bool = False
    ) -> str:
        """Use Ollama LLM to synthesize optical product recommendations with guardrails."""
        focus_instruction = (
            "El cliente busca precio accesible. Compara tiendas y destaca la alternativa más económica del catálogo."
            if is_cheap_intent
            else "Recomienda la opción más adecuada según la necesidad del cliente y compara tiendas objetivamente."
        )

        prompt = (
            "Eres un Asesor Experto en Ópticas en Chile (GMO, Place Vendôme, Rotter & Krauss, Schilling).\n"
            f"Consulta del cliente: '{user_query}'\n\n"
            "Catálogo disponible verificado:\n"
            f"{matched_products_context}\n\n"
            "Reglas y Guardrails obligatorios:\n"
            f"1. {focus_instruction}\n"
            "2. Cita únicamente productos, tiendas y precios reales presentes en el catálogo disponible. No inventes stock ni marcas.\n"
            "3. No des diagnósticos ni recetas médicas; si consultan por graduación o dioptrías, recuerda consultar a un oftalmólogo.\n"
            "4. Mantén un tono profesional, neutral y objetivo. No descalifiques ninguna tienda.\n"
            "5. Responde conciso en 2 a 3 oraciones completas con punto final.\n\n"
            "Recomendación experta:"
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 130,    # Prevent sentence truncation
                "num_thread": 4,       # Optimized multi-threading
                "temperature": 0.2,    # Deterministic and fact-grounded
                "top_k": 15,
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
                        return _clean_trailing_sentence(raw_ans) if raw_ans else "Opciones encontradas en catálogo:"
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


ollama_service = OllamaService()