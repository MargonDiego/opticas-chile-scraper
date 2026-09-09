import logging
from typing import List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Client for Ollama LLM and Vector Embedding services."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.llm_model = settings.OLLAMA_LLM_MODEL
        self.timeout = httpx.Timeout(60.0, connect=5.0)

    def _get_candidate_urls(self) -> List[str]:
        candidates = [self.base_url]
        for fallback in ["http://host.docker.internal:11434", "http://172.17.0.1:11434", "http://192.168.1.85:11434", "http://127.0.0.1:11434"]:
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text vector embedding via Ollama."""
        if not text or not text.strip():
            return None

        payload = {
            "model": self.embed_model,
            "prompt": text.strip(),
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/embeddings"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        return data.get("embedding")
            except Exception as e:
                logger.debug(f"Ollama embedding attempt failed on {base}: {e}")
                continue

        return None

    async def ask_advisor(
        self, user_query: str, matched_products_context: str
    ) -> str:
        """Use Ollama LLM to synthesize optical product recommendations."""
        system_prompt = (
            "Eres un Asesor Experto en Ópticas en Chile. "
            "Ayudas a los usuarios a comparar lentes ópticos, lentes de sol y lentes de contacto "
            "entre tiendas como GMO, Rotter & Krauss, Schilling, Place Vendôme y Econópticas. "
            "Responde de forma clara, amigable y destaca precios en CLP y diferencias de marcas."
        )

        prompt = (
            f"{system_prompt}\n\n"
            f"Consulta del usuario: {user_query}\n\n"
            f"Productos encontrados en catálogo:\n{matched_products_context}\n\n"
            f"Recomendación para el usuario:"
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/generate"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        return data.get("response", "No se pudo generar respuesta del asesor.")
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


ollama_service = OllamaService()