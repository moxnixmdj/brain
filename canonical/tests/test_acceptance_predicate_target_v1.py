"""The acceptance-predicate census: what it must not get wrong, and the debt it pins.

Two ways this could mislead:

  * calling a content check "transport" because the field is named after a hash — a digest
    comparison against the source is a real check, and `file.copy.v1` would be slandered;
  * calling a display string or an unthresholded score a "definite" fix — only a computed
    boolean the capability also declares earns that word.

Both are tested. The nine known cases are pinned as debt: the list may shrink, never grow.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from acceptance_predicate_target_probe_20261112 import (  # noqa: E402
    NO_SOURCE,
    READS_INDEPENDENT_CHECK,
    READS_NEITHER,
    READS_OUTCOME,
    READS_TRANSPORT_NO_OUTCOME,
    READS_TRANSPORT_OUTCOME_AVAILABLE,
    _computed_assignments,
    classify,
    run,
)

KNOWN = {
    READS_INDEPENDENT_CHECK,
    READS_OUTCOME,
    READS_TRANSPORT_OUTCOME_AVAILABLE,
    READS_TRANSPORT_NO_OUTCOME,
    READS_NEITHER,
    NO_SOURCE,
}

#: Capabilities whose adapter computes and declares a boolean answer while the registry accepts on
#: `output_verified`. This is debt. Nothing may be added to it; entries are removed by repointing
#: the predicate and re-measuring.
DEFINITE_DEBT = {
    "python.patch.search.test_guided.ast.v1",
    "python.software.repair.guided.provenance.coupled.v1",
    "python.software.repair.loop.coupled.ast.v1",
    "python.software.repair.loop.strict_progress.ast.v1",
    "python.software.repair.loop.test_guided.ast.v1",
    "python.software.repair.measured_acceptance.v1",
    "python.software.repair.semantic_acceptance.v1",
    "python.software.request.semantic_behavior.compile.v1",
    "python.task.acceptance.measured.objective.v1",
}


def _classify(tmp_path: Path, source: str, *, expect_type="field_equals",
              field="output_verified", declared=("output_verified", "pass")) -> dict:
    (tmp_path / "adapter.py").write_text(source, encoding="utf-8")
    row = {
        "action_template": {"expect": {"type": expect_type, "field": field, "value": True}},
        "result_fields": list(declared),
        "source": {"adapter_path": "adapter.py"},
    }
    return classify("synthetic", row, tmp_path)


def test_a_digest_comparison_is_not_transport(tmp_path):
    source = "def run():\n    return {'destination_sha256': compute()}\n"
    result = _classify(tmp_path, source, expect_type="file_sha256_matches",
                       field="destination_sha256")
    assert result["class"] == READS_INDEPENDENT_CHECK


def test_a_declared_computed_boolean_is_the_definite_case(tmp_path):
    source = "def run(w):\n    r = {}\n    r['pass'] = w is not None\n    r['output_verified'] = True\n    return r\n"
    result = _classify(tmp_path, source)
    assert result["class"] == READS_TRANSPORT_OUTCOME_AVAILABLE
    assert result["candidate_outcome_field"] == "pass"
    assert result["confidence"] == "DEFINITE"


def test_an_undeclared_outcome_is_only_a_candidate(tmp_path):
    source = "def run(w):\n    r = {}\n    r['pass'] = w is not None\n    return r\n"
    result = _classify(tmp_path, source, declared=("output_verified",))
    assert result["class"] == READS_TRANSPORT_OUTCOME_AVAILABLE
    assert result["candidate_declared_in_result_fields"] is False
    assert result["confidence"] == "CANDIDATE"


def test_a_literal_is_not_computed():
    tree = ast.parse("r = {}\nr['pass'] = True\nr['pass'] = check()\n")
    assert _computed_assignments(tree, "pass") == 1
    assert _computed_assignments(tree, "missing") == 0


def test_the_partition_holds_and_nothing_new_enters_the_debt_list():
    result = run()
    records, summary = result["records"], result["summary"]
    assert sum(summary["classes"].values()) == len(records) == summary["capabilities"]
    assert set(summary["classes"]) <= KNOWN

    definite = {
        r["capability_id"] for r in records
        if r.get("confidence") == "DEFINITE"
    }
    # The list may shrink. It may never grow without a reviewer noticing.
    assert definite <= DEFINITE_DEBT, sorted(definite - DEFINITE_DEBT)
    assert summary["definite"] == len(definite)
    assert summary["reads_transport_while_outcome_available"] == (
        summary["definite"]
        + sum(1 for r in result["fix_list"] if r["confidence"] == "CANDIDATE")
    )


def test_every_definite_case_reads_a_transport_field_and_offers_a_boolean():
    for row in run()["fix_list"]:
        if row["confidence"] != "DEFINITE":
            continue
        assert row["expect_field"] == "output_verified"
        assert row["outcome_declared"] is True
        assert row["should_read"] in {"pass", "accepted", "success"}


def test_the_run_is_deterministic():
    import json

    assert json.dumps(run(), sort_keys=True) == json.dumps(run(), sort_keys=True)
