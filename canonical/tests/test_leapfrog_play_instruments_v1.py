"""Tests for the two instruments behind leapfrog Plays 4 and 5.

Both tools make a claim about the tree, and both claims are only readable if the
instrument is shown working on cases where the answer is known:

  1. the bucketed law store must actually return the right law (a fast index that
     returns nothing is worse than a slow one), and its removal control must key on
     the law id -- a control that keys on the projection key passes a broken store;
  2. the mutation probe (Play 6) must rewrite operators at their own AST spans and never
     inside a string, must be deterministic, and must leave every module byte-identical;
  3. the refusal ledger must count a refusal nested inside `commits[].modules[]`,
     must not count the empty `"refusal": ""` placeholder, and must count bare
     `REFUSED` as an untyped reason rather than as evidence of checkability.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.tools import measure_law_store_flat_lookup_v1 as L  # noqa: E402
from canonical.tools import mutation_admission_probe_v1 as M  # noqa: E402
from canonical.tools import refusal_ledger_v1 as R  # noqa: E402


def test_bucketed_store_returns_the_law_and_beats_linear_at_500():
    laws = L.make_laws(500)
    bucketed, linear = L.Bucketed(laws), L.Linear(laws)
    for law in laws[:50]:
        hits = bucketed.lookup(tuple(law["key"]))
        assert any(hit["id"] == law["id"] for hit in hits), "index lost a stored law"
        assert any(hit["id"] == law["id"] for hit in linear.lookup(tuple(law["key"])))
    row = L.measure(500, queries=40, repeats=3)
    assert row["removal_control"]["control_ok"] is True
    assert row["speedup"] > 1.0
    assert row["bucketed"]["hits"] == row["bucketed"]["queries"]


def test_flat_ratio_threshold_is_the_kill_criterion():
    result = L.run(sizes=(10, 100, 1000))
    # No 5,000-law row -> the claim is not made rather than defaulted to True.
    assert result["ratios"]["bucketed_5000_over_10"] is None
    assert result["flat_claim_holds"] is False
    assert result["model_calls"] == 0
    assert result["measures"] == "INDEX_LOOKUP_ONLY__NOT_SOLVER_QUALITY"


def test_ledger_counts_nested_refusals_and_ignores_empty_placeholders():
    doc = {
        "commits": [
            {
                "modules": [
                    {
                        "verdict": "REFUSED",
                        "refusals": [
                            {"refusal": "REFUSED__NO_VALUE_IN_THE_INSTRUCTION",
                             "why": "the sentence names nothing checkable"},
                            {"refusal": ""},
                        ],
                    }
                ]
            }
        ],
        "refusal": "",
        "status": "SUCCEEDED",
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "receipt.json").write_text(json.dumps(doc), encoding="utf-8")
        (root / "broken.json").write_text("{not json", encoding="utf-8")
        ledger = R.build(root)

    # Three real decisions (the file's own status, the module verdict, the typed refusal)
    # and nothing from the empty `"refusal": ""` placeholder.
    assert ledger["decisions_recorded"] == 3
    assert ledger["outcomes"]["REFUSED_WITH_REASON"] == 1
    assert ledger["outcomes"]["REFUSED"] == 1
    assert ledger["outcomes"]["SUCCEEDED"] == 1
    assert ledger["json_files_scanned"] == 1
    assert ledger["typed_reason_count"] == 1
    # Bare `REFUSED` is a reason that names nothing; it must not inflate checkability.
    assert ledger["typed_reason_share"] == 0.5
    assert ledger["mechanical_share_of_typed_reasons"] == 0.0
    assert R.classify_reason("REFUSED") == "UNCLASSIFIED"
    assert R.classify_reason("REFUSED__LABEL_NOT_ON_THE_PAGE") == "MECHANICAL"
    assert R.is_typed("REFUSED") is False


def test_ledger_non_success_denominator_is_separate_from_decision_share():
    doc = [{"status": "SUCCEEDED"}, {"status": "FAILED"}, {"refusal": "FAIL_CLOSED"}]
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "d.json").write_text(json.dumps(doc), encoding="utf-8")
        ledger = R.build(root)
    assert ledger["decisions_recorded"] == 3
    assert ledger["refusal_share"] == round(1 / 3, 4)
    assert ledger["refusal_share_of_non_success"] == 0.5


def test_mutants_are_ast_spans_not_regex_rewrites():
    """A mutation must change one operator at its own span, and never inside a string."""
    source = (
        "def f(x):\n"
        '    """usage: f <repo> [module]"""\n'
        "    if x < 3 and not x:\n"
        "        return x == 3\n"
        "    return 0\n"
        '\n'
        'if __name__ == "__main__":\n'
        "    print(f(1) == 0)\n"
    )
    got = M.mutants(source, 12, seed=0)
    kinds = {c["mutator"] for c in got}
    assert "cmp_<" in kinds and "bool_swap" in kinds and "drop_not" in kinds
    for candidate in got:
        assert candidate["before"] != candidate["after"]
        # One line differs, and it is the candidate's own line.
        before_lines = source.splitlines()
        after_lines = candidate["text"].splitlines()
        assert len(before_lines) == len(after_lines)
        diff = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        assert diff == [candidate["line"] - 1]
        assert '"""' not in candidate["after"], "mutation reached a string literal"
        assert "__main__" not in candidate["after"], "mutation reached the CLI guard"


def test_mutant_generation_is_deterministic():
    source = (M.ROOT / "canonical/swe_kernel/rule_expiry_v1.py").read_text(encoding="utf-8")
    first = M.mutants(source, 6, seed=len(source))
    second = M.mutants(source, 6, seed=len(source))
    assert [(c["mutator"], c["line"], c["after"]) for c in first] == \
           [(c["mutator"], c["line"], c["after"]) for c in second]


def test_probe_counts_only_discriminating_kills_and_restores_bytes(tmp_path=None):
    """Integration probe: baseline runs, one mutant, file restored exactly."""
    result = M.probe_module(M.ROOT / "canonical/swe_kernel/rule_expiry_v1.py", limit=1,
                            timeout=180.0, baseline_repeats=1)
    assert result["restored_exactly"] is True
    assert result["baseline_tests_ran"] and result["baseline_tests_ran"] > 0
    assert len(result["mutants"]) == 1
    kill = result["mutants"][0]
    # A kill only counts when the suite actually ran and the module still imported.
    if kill["killed"] and (kill["import_failure"] or not kill["tests_ran"]):
        assert kill["discriminating"] is False
