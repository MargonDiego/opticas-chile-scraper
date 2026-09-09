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
        """Use Ollama LLM to synthesize optical product recommendations quickly."""
        focus_instruction = (
            "El cliente busca la opción más conveniente, económica y de buena calidad al menor precio en CLP."
            if is_cheap_intent
            else "Recomienda el modelo más adecuado justificando según la necesidad del cliente (protección UV, comodidad, actividad o diseño)."
        )

        prompt = (
            "Eres un Asesor Óptico experto en Chile.\n"
            f"Pregunta del cliente: '{user_query}'\n\n"
            "Opciones disponibles en catálogo (ordenadas por conveniencia):\n"
            f"{matched_products_context}\n\n"
            f"Instrucciones:\n"
            f"- {focus_instruction}\n"
            "- Menciona la marca, modelo y precio exacto en CLP.\n"
            "- Sé directo, profesional y claro (máximo 2 a 3 oraciones).\n\n"
            "Recomendación experta:"
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 65,     # Balanced for high quality & fast CPU latency
                "num_thread": 4,       # Full hardware threads
                "temperature": 0.2,    # Focused yet natural
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
                        data = res.json()
                        return data.get("response", "No se pudo generar respuesta del asesor.")
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


ollama_service = OllamaService()