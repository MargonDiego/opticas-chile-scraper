#!/usr/bin/env python3
"""Ranking-quality harness for ``POST /api/products/search/semantic``.

The semantic endpoint mixes pgvector similarity with lexical scoring, and its
response exposes ``similarity_score`` for the rows that came from the vector
candidate set. That makes ranking quality observable from the outside: this
script runs a fixed query set against a live deployment and checks declared
invariants instead of eyeballing the JSON.

Read-only by design: the only endpoint it calls is the public semantic search.
It never touches the admin or scrape routes.

Usage:
    BASE_URL=https://api.example.com API_KEY=... uv run python tools/eval_search.py
    uv run python tools/eval_search.py --base-url http://localhost:8000 --api-key secret

Environment variables ``BASE_URL`` / ``API_KEY`` are used when the matching
flag is omitted. Exit code is 1 when any case fails, 0 otherwise. Transport
errors, 401/403, other non-2xx statuses and malformed JSON bodies become
explicit FAIL rows, never tracebacks.
"""

import argparse
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

SEMANTIC_SEARCH_PATH = "/api/products/search/semantic"
DEFAULT_TOP_K = 10
DEFAULT_TIMEOUT_SECONDS = 60.0

# Extend by appending another dict. Supported keys:
#
#   name               label shown in the table (required)
#   query              query string sent to the endpoint (required)
#   limit              result count to request (default: DEFAULT_TOP_K)
#   request            extra request fields, e.g. {"store": "gmo"}
#   min_results        results expected (default: 1)
#   expect_store       every result must be from this store
#   expect_category    every result must have this category
#   keyword_min_count  {"keyword": "Kids", "min_count": 2, "top_k": 10,
#                       "fields": ["model_name", "description"]}
#                      ``fields`` defaults to ["model_name"]; set it explicitly
#                      so the case states which field it is really checking.
#   top1_must_contain  the first result's model name must contain this
#   min_mean_similarity mean similarity over scored results must be >= value
#   min_scored_ratio   fraction of results that must carry a non-null
#                      similarity_score (proves the vector path contributed)
CASES: List[Dict[str, Any]] = [
    {
        # "infantil" does not exist in the catalog; a healthy embedding should
        # surface the kids frames whose model names say "Kids". The lexical
        # description path can also produce this, so min_scored_ratio is what
        # proves the vector path participated.
        "name": "kids-synonym",
        "query": "armazon infantil",
        "keyword_min_count": {
            "keyword": "Kids",
            "min_count": 2,
            "top_k": 10,
            "fields": ["model_name"],
        },
        "min_scored_ratio": 0.8,
    },
    {
        "name": "store-facet-gmo",
        "query": "lentes de sol polarizados",
        "request": {"store": "gmo"},
        "expect_store": "gmo",
    },
    {
        # Checks model_name and description for "Polariz" (polarizado /
        # polarizada). Matching "Polar" was a false positive: it passed on the
        # brand "Polaroid" while proving nothing about polarized lenses.
        "name": "polarized-context",
        "query": "lentes polarizados para playa",
        "keyword_min_count": {
            "keyword": "Polariz",
            "min_count": 2,
            "top_k": 10,
            "fields": ["model_name", "description"],
        },
    },
    {
        # Control: an exact product word must rank first.
        "name": "exact-product-control",
        "query": "Aviator",
        "top1_must_contain": "Aviator",
    },
    {
        # Regression gate: if every similarity_score comes back null, the mean
        # cannot be computed and this case fails even though 0.4 could not be
        # compared. A working vector path scores comfortably above 0.4 for a
        # query whose vocabulary exists in the catalog.
        "name": "vector-scores-sanity",
        "query": "lentes de sol polarizados",
        "limit": 10,
        "min_mean_similarity": 0.4,
        "min_scored_ratio": 0.8,
    },
]


class CaseFailure(Exception):
    """A case-level failure reported as a FAIL row instead of a traceback."""


def _payload_problem(payload: Any) -> Optional[str]:
    """Return a human message when the JSON body is not a list of objects."""
    if not isinstance(payload, list):
        return f"malformed payload: expected a JSON array, got {type(payload).__name__}"
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            return (
                f"malformed payload: result #{index} is {type(item).__name__}, "
                "expected an object"
            )
    return None



def fetch_results(
    client: httpx.Client,
    base_url: str,
    api_key: Optional[str],
    case: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], float]:
    """Call the semantic endpoint once and return (results, latency_ms).

    Raises ``CaseFailure`` for every unusable answer (transport error, 401/403,
    another non-2xx status, non-JSON body, or a JSON body that is not a list of
    objects) so the caller can print a FAIL row instead of a traceback.
    """
    payload: Dict[str, Any] = {
        "query": case["query"],
        "limit": case.get("limit", DEFAULT_TOP_K),
    }
    payload.update(case.get("request", {}))
    headers = {"X-API-Key": api_key} if api_key else {}

    started = time.perf_counter()
    try:
        response = client.post(
            f"{base_url.rstrip('/')}{SEMANTIC_SEARCH_PATH}",
            json=payload,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise CaseFailure(f"request failed: {type(exc).__name__}: {exc}") from None
    latency_ms = (time.perf_counter() - started) * 1000.0

    if response.status_code in (401, 403):
        raise CaseFailure(
            f"HTTP {response.status_code} {response.reason_phrase}: rejected the API key "
            "(pass --api-key or set API_KEY)"
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        raise CaseFailure(
            f"HTTP {response.status_code} {response.reason_phrase} from {SEMANTIC_SEARCH_PATH}"
        ) from None

    try:
        body = response.json()
    except ValueError:
        raise CaseFailure(
            "malformed payload: response is not valid JSON "
            f"(content-type={response.headers.get('content-type', 'unknown')})"
        ) from None

    problem = _payload_problem(body)
    if problem:
        raise CaseFailure(problem)
    return body, latency_ms


def mean_similarity(results: List[Dict[str, Any]]) -> Optional[float]:
    """Mean similarity over the rows that actually carry a vector score."""
    scores = [
        float(item["similarity_score"])
        for item in results
        if item.get("similarity_score") is not None
    ]
    if not scores:
        return None
    return round(statistics.fmean(scores), 4)


def check_case(
    case: Dict[str, Any], results: List[Dict[str, Any]]
) -> List[str]:
    """Return the list of failed invariants for one case (empty means pass)."""
    failures: List[str] = []

    min_results = case.get("min_results", 1)
    if len(results) < min_results:
        failures.append(f"expected at least {min_results} results, got {len(results)}")

    expect_store = case.get("expect_store")
    if expect_store:
        wrong = [item.get("store") for item in results if item.get("store") != expect_store]
        if wrong:
            failures.append(f"expected store={expect_store}, got {sorted(set(wrong))}")

    expect_category = case.get("expect_category")
    if expect_category:
        wrong = [
            item.get("category") for item in results if item.get("category") != expect_category
        ]
        if wrong:
            failures.append(
                f"expected category={expect_category}, got {sorted(set(map(str, wrong)))}"
            )

    keyword_rule = case.get("keyword_min_count")
    if keyword_rule:
        keyword = str(keyword_rule["keyword"]).lower()
        top_k = int(keyword_rule.get("top_k", DEFAULT_TOP_K))
        min_count = int(keyword_rule["min_count"])
        fields = list(keyword_rule.get("fields", ["model_name"]))
        matches = sum(
            1
            for item in results[:top_k]
            if any(keyword in str(item.get(field) or "").lower() for field in fields)
        )
        if matches < min_count:
            failures.append(
                f"expected '{keyword_rule['keyword']}' in >= {min_count} of top {top_k} "
                f"(fields: {', '.join(fields)}), got {matches}"
            )

    top1_must_contain = case.get("top1_must_contain")
    if top1_must_contain:
        top_model = str(results[0].get("model_name", "")) if results else ""
        if top1_must_contain.lower() not in top_model.lower():
            failures.append(
                f"expected top result to contain '{top1_must_contain}', got '{top_model}'"
            )

    min_mean = case.get("min_mean_similarity")
    if min_mean is not None:
        score = mean_similarity(results)
        if score is None:
            failures.append(
                "min_mean_similarity set but every similarity_score was null: "
                "the vector path contributed nothing"
            )
        elif score < float(min_mean):
            failures.append(f"mean similarity {score} < {min_mean}")

    min_scored_ratio = case.get("min_scored_ratio")
    if min_scored_ratio is not None:
        if not results:
            failures.append(
                "min_scored_ratio set but the endpoint returned no results to score"
            )
        else:
            scored = sum(
                1 for item in results if item.get("similarity_score") is not None
            )
            ratio = scored / len(results)
            if ratio < float(min_scored_ratio):
                failures.append(
                    f"only {scored}/{len(results)} results carried a similarity_score "
                    f"({ratio:.2f} < {min_scored_ratio}): the vector path did not "
                    "contribute to these results"
                )

    return failures


def _shorten(value: str, width: int) -> str:
    return value if len(value) <= width else value[: width - 3] + "..."


def run(
    base_url: str,
    api_key: Optional[str],
    timeout: float,
    cases: Optional[List[Dict[str, Any]]] = None,
    client: Optional[httpx.Client] = None,
) -> int:
    """Run every case, print the summary table, and return the exit code.

    ``client`` is injectable so tests can drive the harness with a mock
    transport; production usage leaves it unset. No case is allowed to raise:
    an unusable answer becomes a FAIL row.
    """
    query_set = CASES if cases is None else cases
    failures_by_case: List[Tuple[str, List[str]]] = []
    failed_count = 0

    header = f"{'query':<38} {'result':<7} {'mean_sim':>9} {'latency_ms':>11}  top-3 model names"
    print(header)
    print("-" * len(header))

    request_client = client if client is not None else httpx.Client(timeout=timeout)
    try:
        for case in query_set:
            try:
                results, latency_ms = fetch_results(
                    request_client, base_url, api_key, case
                )
                failures = check_case(case, results)
            except CaseFailure as exc:
                results, latency_ms = [], 0.0
                failures = [str(exc)]
            except Exception as exc:  # noqa: BLE001 - a harness must never traceback
                results, latency_ms = [], 0.0
                failures = [f"unexpected error: {type(exc).__name__}: {exc}"]

            if failures:
                failed_count += 1
                failures_by_case.append((case.get("name", case["query"]), failures))

            score = mean_similarity(results)
            score_text = f"{score:.4f}" if score is not None else "n/a"
            top_models = " | ".join(
                _shorten(str(item.get("model_name", "")), 34) for item in results[:3]
            )
            print(
                f"{_shorten(str(case['query']), 38):<38} "
                f"{'FAIL' if failures else 'PASS':<7} "
                f"{score_text:>9} "
                f"{latency_ms:>11.0f}  {top_models or '-'}"
            )
    finally:
        if client is None:
            request_client.close()

    if failures_by_case:
        print("\nFailures:")
        for name, failures in failures_by_case:
            for failure in failures:
                print(f"  - {name}: {failure}")

    total = len(query_set)
    print(f"\n{total - failed_count}/{total} cases passed.")
    return 1 if failed_count else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only ranking-quality checks for the semantic search endpoint."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL"),
        help="API base URL (default: $BASE_URL)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY"),
        help="Public API key sent as X-API-Key (default: $API_KEY)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    args = parser.parse_args(argv)

    if not args.base_url:
        print("error: BASE_URL is not set (use --base-url or the BASE_URL env var)", file=sys.stderr)
        return 2

    return run(args.base_url, args.api_key, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
