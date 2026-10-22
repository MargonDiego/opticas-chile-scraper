import json
import logging
import time
from typing import AsyncIterator, List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)

# Health probes walk every candidate host, so each attempt needs a short
# timeout and the whole walk needs a hard budget: a dead Ollama must never
# slow the healthcheck down.
HEALTH_PROBE_PER_HOST_TIMEOUT_SECONDS = 0.5
HEALTH_PROBE_TOTAL_TIMEOUT_SECONDS = 1.4

# Fallback answers, extracted as constants so both transports — and the SSE
# endpoint's end-of-stream cleanup — reference byte-identical strings.
EMPTY_ANSWER_FALLBACK = "Encontré las siguientes opciones destacadas en el catálogo:"
UNREACHABLE_FALLBACK = "Encontré las siguientes opciones destacadas en el catálogo según tu búsqueda:"


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


def _build_advisor_prompt(
    user_query: str,
    matched_products_context: str,
    is_cheap_intent: bool = False,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    detected_brand: Optional[str] = None,
    target_store: Optional[str] = None,
    requires_discount: bool = False,
) -> str:
    """Compose the advisor prompt.

    Shared verbatim by ``ask_advisor`` (non-streaming) and
    ``ask_advisor_stream`` (SSE) so the two transports cannot drift apart.
    """
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
        "Recomienda directamente el primer producto de la lista indicando su nombre completo, tienda y precio exacto."
        if (is_cheap_intent or budget_min or budget_max)
        else "Recomienda la opción más adecuada de la lista y compara tiendas objetivamente."
    )

    return (
        "Eres un Asesor Experto en Ópticas en Chile.\n"
        f"Consulta del usuario: '{user_query}'\n"
        f"{constraints_str}"
        "Catálogo de productos disponibles (ordenados por conveniencia):\n"
        f"{matched_products_context}\n\n"
        "Reglas obligatorias:\n"
        f"1. {focus_instruction}\n"
        "2. Usa ÚNICAMENTE los productos, tiendas y precios reales de la lista. NUNCA inventes productos ni uses marcadores como [Marca], [Nombre] o [Tienda].\n"
        "3. No des diagnósticos ni recetas médicas.\n"
        "4. Escribe 1 o 2 oraciones concisas y fluidas en español chileno, terminando con punto final.\n\n"
        "Recomendación:"
    )


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
        candidates = [self.base_url, "http://host.docker.internal:11434", "http://192.168.1.85:11434", "http://127.0.0.1:11434"]
        unique = []
        for c in candidates:
            if c and c not in unique:
                unique.append(c)
        return unique

    async def ping(self) -> bool:
        """Cheap reachability probe used by the health endpoint.

        Walks the same candidate hosts as ``get_embedding``/``ask_advisor`` so a
        cold start with an unreachable primary but a live fallback reports
        healthy. Each host gets a short timeout and the whole walk is bounded,
        because a dead Ollama must never slow the healthcheck down. The first
        answering host is remembered in ``_working_url`` so later calls skip the
        dead primary.
        """
        deadline = time.monotonic() + HEALTH_PROBE_TOTAL_TIMEOUT_SECONDS
        async with httpx.AsyncClient() as client:
            for base in self._get_candidate_urls():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                timeout = httpx.Timeout(
                    min(HEALTH_PROBE_PER_HOST_TIMEOUT_SECONDS, remaining),
                    connect=min(HEALTH_PROBE_PER_HOST_TIMEOUT_SECONDS, remaining),
                )
                try:
                    res = await client.get(f"{base.rstrip('/')}/api/version", timeout=timeout)
                    if res.status_code == 200:
                        self._working_url = base
                        return True
                except Exception as e:
                    logger.debug(f"Ollama health probe failed on {base}: {e}")
                    continue
        return False

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate a text vector embedding via Ollama.

        The caller owns the length policy: product text is composed (and
        truncated at a word boundary) by ``src.services.embedding_text``, and
        queries are short by construction. Truncating here as well used to cut
        product context to 150 characters and make descriptive queries
        unmatchable, so no blind cap is applied anymore.
        """
        if not text or not text.strip():
            return None

        payload = {
            "model": self.embed_model,
            "prompt": text.strip(),
            "keep_alive": "30m",
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
        prompt = _build_advisor_prompt(
            user_query,
            matched_products_context,
            is_cheap_intent=is_cheap_intent,
            budget_min=budget_min,
            budget_max=budget_max,
            detected_brand=detected_brand,
            target_store=target_store,
            requires_discount=requires_discount,
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": 55,
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
                        return _clean_trailing_sentence(raw_ans) if raw_ans else EMPTY_ANSWER_FALLBACK
            except Exception as e:
                logger.debug(f"Ollama chat attempt failed on {base}: {e}")
                continue

        return UNREACHABLE_FALLBACK

    async def ask_advisor_stream(
        self,
        user_query: str,
        matched_products_context: str,
        is_cheap_intent: bool = False,
        budget_min: Optional[int] = None,
        budget_max: Optional[int] = None,
        detected_brand: Optional[str] = None,
        target_store: Optional[str] = None,
        requires_discount: bool = False,
    ) -> AsyncIterator[str]:
        """Streaming twin of ``ask_advisor``: same prompt and options, but the
        Ollama answer is consumed incrementally from its NDJSON stream.

        Yields text chunks as they arrive. Raises ``ConnectionError`` when no
        candidate host answered, so the caller can surface the failure after
        it has already delivered the product cards. An answer that completed
        with no text yields the same fallback sentence ``ask_advisor`` uses.

        Once the first chunk has been yielded a transport failure is NOT
        retried on another host — retrying would replay the answer from the
        start and show the user the text twice.
        """
        prompt = _build_advisor_prompt(
            user_query,
            matched_products_context,
            is_cheap_intent=is_cheap_intent,
            budget_min=budget_min,
            budget_max=budget_max,
            detected_brand=detected_brand,
            target_store=target_store,
            requires_discount=requires_discount,
        )

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "30m",
            "options": {
                "num_predict": 55,
                "temperature": 0.1,
                "top_k": 10,
            },
        }

        for base in self._get_candidate_urls():
            url = f"{base}/api/generate"
            # Declared before the try so the except clause can always read it:
            # once ONE chunk has been yielded to the client, this host is no
            # longer safely retryable.
            emitted = False
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream("POST", url, json=payload) as res:
                        if res.status_code != 200:
                            continue
                        async for line in res.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                payload_obj = json.loads(line)
                            except json.JSONDecodeError:
                                # Ollama only ever sends NDJSON here; skip a
                                # malformed line instead of killing the answer.
                                continue
                            if not isinstance(payload_obj, dict):
                                # Valid JSON but not an object — no chunk in it.
                                continue
                            chunk = payload_obj.get("response", "")
                            if chunk:
                                emitted = True
                                yield chunk
                        # Pin only AFTER the stream completed: a host that
                        # merely sent a status line (or died mid-body) has not
                        # proven itself.
                        self._working_url = base
                        if emitted:
                            return
                        yield EMPTY_ANSWER_FALLBACK
                        return
            except Exception as e:
                if emitted:
                    # Tokens from this answer already reached the client.
                    # Retrying another host would re-POST the prompt and
                    # replay the whole answer from the start — the caller
                    # would see it twice. Surface the failure instead.
                    raise
                logger.debug(f"Ollama streaming chat attempt failed on {base}: {e}")
                continue

        raise ConnectionError("Ollama did not answer on any candidate host")


ollama_service = OllamaService()