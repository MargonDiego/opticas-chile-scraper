"""Unit tests for the ranking-quality harness (no live server).

The harness is meant to be usable as a deployment gate, so its failures must be
observable FAIL rows -- never a traceback and never a false PASS driven by a
lexical coincidence.
"""

import httpx
import pytest

from tools.eval_search import CASES, CaseFailure, check_case, fetch_results, run


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _case(**overrides):
    base = {"name": "test-case", "query": "aviator"}
    base.update(overrides)
    return base


def _result(**overrides):
    item = {
        "id": "p1",
        "store": "gmo",
        "brand": "Ray-Ban",
        "model_name": "Aviator",
        "category": "opticos",
        "similarity_score": 0.8,
    }
    item.update(overrides)
    return item


def _run_with(handler, case) -> int:
    with _client(handler) as client:
        return run("http://test", None, 5.0, cases=[case], client=client)


def test_401_is_reported_as_a_fail_row(capsys):
    def handler(_request):
        return httpx.Response(401, json={"detail": "unauthorized"})

    assert _run_with(handler, _case()) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "HTTP 401" in out
    assert "API key" in out


def test_non_list_payload_is_reported_as_a_fail_row(capsys):
    def handler(_request):
        return httpx.Response(200, json={"detail": "not a list"})

    assert _run_with(handler, _case()) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "expected a JSON array, got dict" in out


def test_non_json_body_is_reported_as_a_fail_row(capsys):
    def handler(_request):
        return httpx.Response(200, text="<html>boom</html>")

    assert _run_with(handler, _case()) == 1
    assert "not valid JSON" in capsys.readouterr().out


def test_transport_error_is_reported_as_a_fail_row(capsys):
    def handler(_request):
        raise httpx.ConnectError("connection refused")

    assert _run_with(handler, _case()) == 1
    assert "ConnectError" in capsys.readouterr().out


def test_passing_case_returns_zero(capsys):
    def handler(_request):
        return httpx.Response(200, json=[_result()])

    assert _run_with(handler, _case(min_mean_similarity=0.4)) == 0
    assert "1/1 cases passed" in capsys.readouterr().out


def test_all_null_scores_fail_the_similarity_threshold():
    case = _case(min_mean_similarity=0.4)
    failures = check_case(case, [_result(similarity_score=None)])

    assert failures
    assert "every similarity_score was null" in failures[0]


def test_all_null_scores_fail_even_when_the_threshold_is_low():
    """A null score must never be treated as a satisfied threshold."""
    failures = check_case(_case(min_mean_similarity=0.0), [_result(similarity_score=None)])

    assert failures


def test_min_scored_ratio_fails_when_only_a_few_rows_are_vector_derived():
    case = _case(min_scored_ratio=0.8)
    results = [
        _result(similarity_score=0.9),
        _result(id="p2", similarity_score=None),
        _result(id="p3", similarity_score=None),
    ]

    failures = check_case(case, results)

    assert failures
    assert "1/3 results carried a similarity_score" in failures[0]


def test_polarized_case_is_not_satisfied_by_the_polaroid_brand():
    case = next(c for c in CASES if c["name"] == "polarized-context")
    polaroid_rows = [
        _result(model_name="Polaroid Kids 0100", description="Armazón de acetato."),
        _result(id="p2", model_name="Polaroid Sun 0200", description="Lente gris."),
    ]

    failures = check_case(case, polaroid_rows)

    assert failures
    assert "Polariz" in failures[0]
    assert "model_name, description" in failures[0]


def test_polarized_case_passes_on_polarized_descriptions():
    case = next(c for c in CASES if c["name"] == "polarized-context")
    results = [
        _result(model_name="Sun 0100", description="Lentes polarizados UV400."),
        _result(id="p2", model_name="Sun 0200", description="Lente polarizada."),
    ]

    assert check_case(case, results) == []


def test_kids_case_requires_the_vector_path_to_contribute():
    case = next(c for c in CASES if c["name"] == "kids-synonym")
    lexical_only = [
        _result(model_name="Polaroid Kids 1", similarity_score=None),
        _result(id="p2", model_name="Polaroid Kids 2", similarity_score=None),
    ]

    failures = check_case(case, lexical_only)

    assert failures
    assert any("similarity_score" in failure for failure in failures)


def test_fetch_results_rejects_non_object_results():
    def handler(_request):
        return httpx.Response(200, json=[1, 2, 3])

    with _client(handler) as client:
        with pytest.raises(CaseFailure, match="result #0 is int"):
            fetch_results(client, "http://test", None, _case())
