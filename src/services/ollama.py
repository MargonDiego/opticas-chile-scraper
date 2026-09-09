import logging
from typing import List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Client for Ollama LLM and Vector Embedding services with CPU optimizations."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.llm_model = settings.OLLAMA_LLM_MODEL
        self.timeout = httpx.Timeout(20.0, connect=1.2)
        self._working_url: Optional[str] = None

    def _get_candidate_urls(self) -> List[str]:
        if self._working_url:
            return [self._working_url]
        candidates = [self.base_url]
        for fallback in ["http://192.168.1.85:11434", "http://host.docker.internal:11434", "http://172.17.0.1:11434", "http://127.0.0.1:11434"]:
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text vector embedding via Ollama."""
        if not text or not text.strip():
            return None

        payload = {
            "model": self.embed_model,
            "prompt": text.strip()[:200],  # Bound prompt length for fast embedding
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/embeddings"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
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
        self, user_query: str, matched_products_context: str
    ) -> str:
        """Use Ollama LLM to synthesize optical product recommendations quickly."""
        prompt = (
            "Eres un Asesor Experto en Ópticas en Chile. "
            "Recomienda brevemente en 2 oraciones la mejor opción entre los productos encontrados destacando precio y calidad.\n\n"
            f"Consulta: {user_query}\n\n"
            f"Productos:\n{matched_products_context}\n\n"
            "Consejo breve:"
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 70,     # Low token budget for fast CPU generation (< 4s)
                "num_thread": 4,       # Use all 4 hardware threads
                "temperature": 0.2,    # Deterministic and direct
                "top_k": 20,
            },
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/generate"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        self._working_url = base
                        data = res.json()
                        return data.get("response", "No se pudo generar respuesta del asesor.")
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


ollama_service = OllamaService()