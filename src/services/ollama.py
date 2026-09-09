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
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text vector embedding via Ollama."""
        if not text or not text.strip():
            return None

        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.embed_model,
            "prompt": text.strip(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding")
                else:
                    logger.warning(
                        f"Ollama embedding failed ({res.status_code}): {res.text}"
                    )
                    return None
        except Exception as e:
            logger.debug(f"Could not connect to Ollama for embedding: {e}")
            return None

    async def ask_advisor(
        self, user_query: str, matched_products_context: str
    ) -> str:
        """Use Ollama LLM to synthesize optical product recommendations."""
        url = f"{self.base_url}/api/generate"

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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("response", "No se pudo generar respuesta del asesor.")
                else:
                    return f"Error en Ollama ({res.status_code}): {res.text}"
        except Exception as e:
            return f"Ollama no disponible en {self.base_url}: {e}"


ollama_service = OllamaService()