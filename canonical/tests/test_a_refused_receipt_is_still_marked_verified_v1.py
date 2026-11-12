"""The last gate of the nine, closed with a receipt instead of an argument.

`python.task.acceptance.measured.objective.v1` was the one capability left reading `output_verified`
because it consumes a content-addressed measurement receipt and no honest one could be fabricated.

It does not need to be fabricated. This test runs the repository's own producer
(`python.repository.acceptance.measure.v1`) against a real fixture, then asks both predicates what
they think of two runs:

  * a genuine pass — the producer measured the subject, the tests passed, the receipt hashes;
  * a refused receipt — one measurement value altered, so the consumer's hash check fails and it
    answers `FAIL_CLOSED`.

Both runs write their answer to disk and mark it `output_verified: True`. `pass` is False in both,
for different and correct reasons. The legacy predicate accepted both; the registry now rejects both.

That is the whole case for the repoint: a gate that says yes to a genuine pass and yes to a refused
receipt is not a gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from a_refused_receipt_is_still_marked_verified_probe_20261112 import (  # noqa: E402
    CAPABILITY_ID,
    REGISTRY,
    apply_predicate,
    run,
)

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_the_registry_now_asks_the_question_the_capability_answers():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    expect = registry[CAPABILITY_ID]["action_template"]["expect"]
    assert expect == {"type": "field_equals", "field": "pass", "value": True}
    assert "pass" in registry[CAPABILITY_ID]["result_fields"]


def test_the_producer_is_the_trees_own_and_it_passes():
    """No fabricated receipt: the producer ran the fixture's own test and measured it."""
    for case in (_report()["genuine_receipt"], _report()["refused_receipt"]):
        assert case["receipt_producer_pass"] is True
        assert case["receipt_producer_status"] == "PASS__CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT"
        assert case["receipt_measurements"]["tests_pass"] is True
        assert case["receipt_measurements"]["test_returncode"] == 0
        assert case["receipt_measurements"]["repository_source_unchanged"] is True


def test_the_consumer_refuses_both_runs_for_its_own_reasons():
    genuine = _report()["genuine_receipt"]
    refused = _report()["refused_receipt"]
    assert genuine["consumer_pass"] is False
    assert genuine["consumer_status"] == "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS"
    assert refused["consumer_pass"] is False
    assert refused["consumer_status"] == "FAIL_CLOSED"
    assert refused["tampered"] is True


def test_both_runs_were_written_and_marked_verified():
    """The transport fact the old predicate was reading: a file exists and its digest matches."""
    for case in (_report()["genuine_receipt"], _report()["refused_receipt"]):
        assert case["consumer_output_verified"] is True
        assert isinstance(case["consumer_output_sha256"], str)
        assert len(case["consumer_output_sha256"]) == 64


def test_the_legacy_predicate_accepted_the_genuine_case_and_the_refused_one():
    for case in (_report()["genuine_receipt"], _report()["refused_receipt"]):
        assert apply_predicate({"type": "field_equals",
                                "field": "output_verified", "value": True},
                               case["result"]) is True


def test_the_live_registry_rejects_both():
    summary = _report()["summary"]
    assert summary["registry_reads_the_outcome"] is True
    assert summary["registry_accepts"] == 0
    assert _report()["registry_accepts_genuine"] is False
    assert _report()["registry_accepts_refused"] is False


def test_nothing_was_written_into_the_repository():
    assert not (ROOT / "receipt.json").exists()
    assert not (ROOT / "answer.json").exists()
    assert _report()["incremental_spend_usd"] == 0
    assert _report()["model_dependency_count"] == 0
