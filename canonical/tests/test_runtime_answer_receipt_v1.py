"""Tests for the runtime answer receipt: budgets, determinism, and whose numbers it reports."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/tools"))
sys.path.insert(0, str(ROOT / "canonical/runtime"))

import runtime_answer_receipt_v1 as R  # noqa: E402

ARTIFACT = ROOT / "canonical/verification/RUNTIME_ANSWER_RECEIPT_20261127_V1.json"


def test_budgets_are_gates_with_stated_numbers():
    assert R.BUDGETS == {"load_p95_ms": 2000.0, "query_p95_ms": 5.0, "total_wall_clock_s": 60.0}


def test_percentile_is_order_statistic_not_interpolation():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert R._pct(values, 0.0) == 1.0
    assert R._pct(values, 0.5) == 3.0
    assert R._pct(values, 1.0) == 5.0
    assert R._pct([], 0.5) == 0.0


def test_queries_are_derived_from_compiled_capability_ids():
    model = {"capabilities": [{"id": "archive.tar_gz.create"}, {"id": "billing.refund.issue"}]}
    queries = R._queries(model, limit=2)
    assert queries == ["archive tar gz create", "billing refund issue"]


def test_receipt_reports_ledger_numbers_and_zero_model_calls():
    receipt = json.loads(ARTIFACT.read_text())
    assert receipt["schema"] == R.SCHEMA
    assert receipt["promotion"]["callable_now"] == 31
    assert receipt["promotion"]["candidates"] == 849
    assert receipt["cost_of_asking"]["model_calls"] == 0
    assert receipt["cost_of_asking"]["network_calls"] == 0
    assert receipt["cost_of_asking"]["prompt_tokens_per_question"] == 0
    assert receipt["artifact"]["bytes"] > 10_000_000
    for key, budget in R.BUDGETS.items():
        assert receipt["checks"][key] <= budget, (key, receipt["checks"][key])
    assert receipt["verdict"] == "FAST"


def test_instrument_cannot_reach_a_network_or_a_model():
    source = (ROOT / "canonical/tools/runtime_answer_receipt_v1.py").read_text()
    for forbidden in ("requests", "urllib", "openai", "anthropic", "socket", "http"):
        assert forbidden not in source, forbidden
    receipt = json.loads(ARTIFACT.read_text())
    assert receipt["questions"]["find_source"]["n"] > 0
    assert receipt["questions"]["composite_can_you_do_this"]["answered"] > 0
