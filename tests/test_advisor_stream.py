"""Tests for POST /api/advisor/chat/stream: auth, SSE ordering, error path.

Follows the established patterns: monkeypatch the ``ollama_service`` singleton
(see ``tests/test_api.py`` / ``tests/test_reindex.py``), seed rows through
``async_session_factory``, and drive the app through
``httpx.AsyncClient`` + ``ASGITransport``.

The NDJSON reader in ``OllamaService.ask_advisor_stream`` is exercised through
``httpx.MockTransport`` (the shim replaces the ``httpx`` name ONLY inside the
ollama module), so real ``aiter_lines`` parsing, non-200 handling, the
empty-answer fallback and the all-hosts-down path run against real code.
"""

import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

import src.main as app_module
import src.services.ollama as ollama_module
from src.config import settings
from src.database import async_session_factory
from src.models import PriceSnapshot, Product
from src.services.ollama import (
    EMPTY_ANSWER_FALLBACK,
    _build_advisor_prompt,
    ollama_service,
)

API_KEY = "test-advisor-stream-key"
STREAM_ENDPOINT = "/api/advisor/chat/stream"
CHAT_ENDPOINT = "/api/advisor/chat"


def _make_product(product_id: str) -> Product:
    return Product(
        id=product_id,
        store="gmo",
        store_product_id=product_id,
        brand="Ray-Ban",
        model_name="Aviator",
        category="opticos",
        url=f"https://example.com/{product_id}",
        description="Armazones ópticos para leer.",
        # The context builder formats the price, so a snapshot is required.
        price_snapshots=[PriceSnapshot(product_id=product_id, price_normal=45000)],
    )


async def _seed(*products: Product) -> None:
    async with async_session_factory() as session:
        for product in products:
            session.add(product)
        await session.commit()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app_module.app), base_url="http://test")


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event, data) pairs; asserts each data is JSON."""
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        event_name = None
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        assert event_name, f"SSE frame without an event name: {block!r}"
        events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def _ndjson_lines(*responses: str) -> list[bytes]:
    """NDJSON bodies the way Ollama sends them: one JSON object per line."""
    return [json.dumps({"response": r}).encode("utf-8") for r in responses]


class _LineStream(httpx.AsyncByteStream):
    """Serve the body one line at a time so ``aiter_lines`` does real work."""

    def __init__(self, lines: list[bytes]):
        self._lines = lines

    async def __aiter__(self):
        for line in self._lines:
            yield line + b"\n"

    async def aclose(self):
        pass


class _BrokenMidStream(httpx.AsyncByteStream):
    """Deliver one chunk, then die — a mid-answer connection failure."""

    async def __aiter__(self):
        yield b'{"response": "Hola "}\n'
        raise httpx.ReadError("connection died mid-stream")

    async def aclose(self):
        pass


def _patch_ollama_http(monkeypatch, handler) -> None:
    """Route the AsyncClients built inside ``src.services.ollama`` to a
    ``httpx.MockTransport``. The shim replaces the ``httpx`` name only in that
    module, so the ASGI test client and the rest of the app are untouched.
    Also clears the host pin so each test walks the full candidate list.
    """
    real_client = httpx.AsyncClient

    def _client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    class _ShimHttpx:
        Timeout = staticmethod(httpx.Timeout)
        AsyncClient = staticmethod(_client_factory)

    monkeypatch.setattr(ollama_service, "_working_url", None)
    monkeypatch.setattr(ollama_module, "httpx", _ShimHttpx)


@pytest.fixture(autouse=True)
def _off_rate_limiter(monkeypatch):
    """This file posts many AI-route requests inside one 60s window; keep the
    shared in-process limiter out of it. Middleware code is untouched — only
    the setting is flipped per test and restored automatically."""
    monkeypatch.setattr(settings, "ENABLE_RATE_LIMITING", False)


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", API_KEY)
    return API_KEY


@pytest.fixture
def no_embeddings(monkeypatch):
    """Skip the (real) embedding call so the pipeline stays lexical and offline."""

    async def _fake_embedding(text: str):
        return None

    monkeypatch.setattr(ollama_service, "get_embedding", _fake_embedding)


async def test_stream_requires_api_key(api_key, no_embeddings):
    async with _client() as client:
        res = await client.post(STREAM_ENDPOINT, json={"message": "busco armazones"})
        assert res.status_code == 401


async def test_stream_rejects_invalid_api_key(api_key, no_embeddings):
    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert res.status_code == 403


async def test_stream_emits_products_before_done_with_ordered_events(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))

    async def _fake_stream(user_query, matched_products_context, **kwargs):
        for chunk in ["Hola ", "mundo."]:
            yield chunk

    monkeypatch.setattr(ollama_service, "ask_advisor_stream", _fake_stream)

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(res.text)
    names = [name for name, _ in events]
    assert names == ["products", "status", "delta", "delta", "done"]
    assert events[1][1] == {"phase": "generating"}

    # The serialized product payload matches the AdvisorChatResponse shape.
    products_data = events[0][1]["products"]
    assert [p["id"] for p in products_data] == ["p1"]
    assert products_data[0]["store"] == "gmo"
    assert products_data[0]["brand"] == "Ray-Ban"

    assert events[2][1] == {"text": "Hola "}
    assert events[3][1] == {"text": "mundo."}
    assert events[-1][1] == {"message": "Hola mundo."}


async def test_stream_emits_products_then_error_when_ollama_is_down(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))

    async def _dead_stream(user_query, matched_products_context, **kwargs):
        raise ConnectionError("ollama is down")
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(ollama_service, "ask_advisor_stream", _dead_stream)

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    # The SSE response itself succeeds: the user still gets the product cards.
    assert res.status_code == 200
    events = _parse_sse(res.text)
    names = [name for name, _ in events]
    assert names == ["products", "status", "error"]
    assert [p["id"] for p in events[0][1]["products"]] == ["p1"]
    assert events[-1][1]["detail"]


async def test_non_streaming_chat_still_returns_same_shape(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))

    async def _fake_ask(user_query, matched_products_context, **kwargs):
        return "Te recomiendo el Ray-Ban Aviator."

    monkeypatch.setattr(ollama_service, "ask_advisor", _fake_ask)

    async with _client() as client:
        res = await client.post(
            CHAT_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) == {"response", "relevant_products"}
    assert data["response"] == "Te recomiendo el Ray-Ban Aviator."
    assert [p["id"] for p in data["relevant_products"]] == ["p1"]


# --- Real NDJSON reader (httpx.MockTransport, no wholesale monkeypatch) -----


async def test_stream_parses_real_ndjson_chunk_lines(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))
    calls: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=_LineStream(_ndjson_lines("Hola ", "mundo.")))

    _patch_ollama_http(monkeypatch, _handler)
    candidates = ollama_service._get_candidate_urls()

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert [n for n, _ in events] == ["products", "status", "delta", "delta", "done"]
    assert events[1][1] == {"phase": "generating"}
    assert events[2][1] == {"text": "Hola "}
    assert events[3][1] == {"text": "mundo."}
    assert events[-1][1] == {"message": "Hola mundo."}

    # One host answered with a complete stream: it is used once and pinned.
    assert len(calls) == 1
    assert json.loads(calls[0].content)["stream"] is True
    assert ollama_service._working_url == candidates[0]


async def test_stream_skips_malformed_ndjson_lines(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            stream=_LineStream(
                [
                    b'{"response": "Hola "}\n',
                    b"this is not json at all\n",  # JSONDecodeError -> skipped
                    b"[1, 2, 3]\n",  # valid JSON, not an object -> skipped
                    b'{"response": "mundo."}\n',
                ]
            ),
        )

    _patch_ollama_http(monkeypatch, _handler)

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    events = _parse_sse(res.text)
    # The two bad lines never reach the client and never kill the stream.
    assert [n for n, _ in events] == ["products", "status", "delta", "delta", "done"]
    assert events[2][1] == {"text": "Hola "}
    assert events[3][1] == {"text": "mundo."}
    assert events[-1][1] == {"message": "Hola mundo."}


async def test_stream_retries_after_non_200_from_first_host(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))
    calls: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(500, text="server exploded")
        return httpx.Response(200, stream=_LineStream(_ndjson_lines("Hola ", "mundo.")))

    _patch_ollama_http(monkeypatch, _handler)
    candidates = ollama_service._get_candidate_urls()
    assert len(candidates) >= 2, "the fixture needs at least two candidate hosts"

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    events = _parse_sse(res.text)
    assert [n for n, _ in events] == ["products", "status", "delta", "delta", "done"]
    assert events[-1][1] == {"message": "Hola mundo."}
    # Pre-first-chunk failures ARE retryable: the second host was tried and
    # the one that completed the stream is the one that gets pinned.
    assert len(calls) == 2
    assert str(calls[0].url) != str(calls[1].url)
    assert ollama_service._working_url == candidates[1]


async def test_mid_stream_failure_is_never_retried(api_key, no_embeddings, monkeypatch):
    """W1 regression: once tokens reached the client, a transport failure must
    NOT re-POST the prompt on another host — that replays the whole answer."""
    await _seed(_make_product("p1"))
    calls: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=_BrokenMidStream())

    _patch_ollama_http(monkeypatch, _handler)

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert [n for n, _ in events] == ["products", "status", "delta", "error"]
    assert events[2][1] == {"text": "Hola "}
    # Exactly ONE host was attempted despite a full candidate list.
    assert len(calls) == 1
    # A host that died mid-body is not proven healthy: no pin.
    assert ollama_service._working_url is None


async def test_stream_empty_answer_is_identical_to_chat_fallback(api_key, no_embeddings, monkeypatch):
    """W2/W4: the empty-answer fallback is byte-identical across transports
    (ask_advisor returns it verbatim; the SSE done must not append '.')."""
    await _seed(_make_product("p1"))

    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            return httpx.Response(200, stream=_LineStream([b'{"done": true}\n']))
        return httpx.Response(200, json={"response": ""})

    _patch_ollama_http(monkeypatch, _handler)

    async with _client() as client:
        stream_res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )
        chat_res = await client.post(
            CHAT_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    stream_events = _parse_sse(stream_res.text)
    assert [n for n, _ in stream_events] == ["products", "status", "delta", "done"]
    assert stream_events[2][1] == {"text": EMPTY_ANSWER_FALLBACK}
    assert stream_events[-1][1] == {"message": EMPTY_ANSWER_FALLBACK}
    assert chat_res.json()["response"] == EMPTY_ANSWER_FALLBACK
    # The real regression this guards against: ":" followed by a cleanup ".".
    assert not stream_events[-1][1]["message"].endswith(":.")


async def test_stream_all_hosts_down_emits_error_with_products(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))
    calls: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("connection refused", request=request)

    _patch_ollama_http(monkeypatch, _handler)
    candidates = ollama_service._get_candidate_urls()

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "busco armazones ópticos para leer"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert [n for n, _ in events] == ["products", "status", "error"]
    assert [p["id"] for p in events[0][1]["products"]] == ["p1"]
    assert events[-1][1]["detail"]
    # Every candidate host was walked before giving up; none is pinned.
    assert len(calls) == len(candidates)
    assert ollama_service._working_url is None


# --- Guardrails -------------------------------------------------------------


async def test_stream_medical_guardrail_skips_llm_entirely(api_key, no_embeddings, monkeypatch):
    await _seed(_make_product("p1"))

    def _unexpected(*args, **kwargs):
        raise AssertionError("the LLM must not be called for a medical query")

    monkeypatch.setattr(ollama_service, "ask_advisor_stream", _unexpected)
    monkeypatch.setattr(ollama_service, "ask_advisor", _unexpected)

    async with _client() as client:
        res = await client.post(
            STREAM_ENDPOINT,
            json={"message": "tengo dolor de cabeza, ¿qué me recomiendas?"},
            headers={"X-API-Key": API_KEY},
        )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    # Products first, then the canned answer: no status, no deltas, no LLM.
    assert [n for n, _ in events] == ["products", "done"]
    assert events[-1][1]["message"].startswith("Para dolores de cabeza")


def test_build_advisor_prompt_matches_pre_change_bytes():
    """Pin the prompt text: extraction into _build_advisor_prompt must be a
    byte-identical move of the original ask_advisor prompt (no prompt drift
    between the twins, no accidental edits)."""
    context = "- [GMO] Ray-Ban Aviator | Precio: $45.000 CLP | Estado: En stock"
    prompt = _build_advisor_prompt(
        "busco armazones para leer",
        context,
        is_cheap_intent=True,
        budget_max=50000,
        detected_brand="Ray-Ban",
        target_store="gmo",
        requires_discount=True,
    )
    expected = (
        "Eres un Asesor Experto en Ópticas en Chile.\n"
        "Consulta del usuario: 'busco armazones para leer'\n"
        "Restricciones activas: Tienda solicitada: GMO. Marca solicitada: Ray-Ban. "
        "Presupuesto máximo: hasta $50,000 CLP. Filtro solicitado: Solo productos con descuento activo.\n"
        "Catálogo de productos disponibles (ordenados por conveniencia):\n"
        "- [GMO] Ray-Ban Aviator | Precio: $45.000 CLP | Estado: En stock\n\n"
        "Reglas obligatorias:\n"
        "1. Recomienda directamente el primer producto de la lista indicando su nombre completo, tienda y precio exacto.\n"
        "2. Usa ÚNICAMENTE los productos, tiendas y precios reales de la lista. "
        "NUNCA inventes productos ni uses marcadores como [Marca], [Nombre] o [Tienda].\n"
        "3. No des diagnósticos ni recetas médicas.\n"
        "4. Escribe 1 o 2 oraciones concisas y fluidas en español chileno, terminando con punto final.\n\n"
        "Recomendación:"
    )
    assert prompt == expected

    # The no-constraints branch: no restriction line, the comparison focus.
    bare = _build_advisor_prompt("hola", "sin resultados")
    assert "Restricciones activas" not in bare
    assert "Recomienda la opción más adecuada de la lista" in bare
    assert "Consulta del usuario: 'hola'" in bare
