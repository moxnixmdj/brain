"""Tests for the history-induced edit grammar.

The rules that carry the round:

  * the grammar is INDUCED from real diffs and never written as an operator list in this file;
  * a task is real only if its test fails at the parent and passes at the commit -- otherwise it is refused;
  * a candidate is applied, judged, and the ORIGINAL BYTES ARE RESTORED even when the candidate breaks the
    file. A tree left modified would make every later measurement a lie;
  * the oracle (the commit's own edit) is EXECUTED, so "expressible" means "passes", not "fires";
  * "solved" is never inferred from a refusal state, and a refusal is always named.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402

DEFECTIVE = '''\
def total(prices):
    result = 0
    for price in prices:
        result -= price
    return result
'''

REPAIRED = '''\
def total(prices):
    result = 0
    for price in prices:
        result += price
    return result
'''

TEST = '''\
from pkg.core import total


def test_total_ignores_negatives():
    assert total([3, -5, 4]) == 2


def test_total_plain():
    assert total([1, 2]) == 3
'''


def _repo(tmp_path: pathlib.Path, name: str, source: str, test: str = TEST) -> pathlib.Path:
    root = tmp_path / name
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "core.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_core.py").write_text(test, encoding="utf-8")
    return root


def test_schema_and_zero_model():
    report = G.measure([], {})
    assert report["schema"] == "BRAIN_HISTORY_INDUCED_EDIT_GRAMMAR_V1"
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert report["totals"]["solved"] == 0


def test_the_grammar_is_induced_from_diffs_and_deduplicated():
    grammar = G.induce_grammar([("a", DEFECTIVE, REPAIRED), ("b", DEFECTIVE, REPAIRED)])
    assert grammar, "a real one-line fix must induce at least one template"
    assert all(template.taught_by for template in grammar), "a template must name the diffs that taught it"
    assert any(template.support >= 2 for template in grammar), "two identical demonstrations must fold"


def test_a_template_fires_only_where_its_precondition_holds():
    grammar = G.induce_grammar([("a", DEFECTIVE, REPAIRED)])
    fired = G.localized_candidates(DEFECTIVE, grammar, function_line=None)
    assert fired, "the template must fire on the defective source"
    assert all("+=" in entry["source"] and "-=" not in entry["source"] for entry in fired)
    assert not G.localized_candidates(REPAIRED, grammar, function_line=None), "it must not fire once fixed"


def test_sites_inside_the_traceback_function_are_searched_first():
    grammar = G.induce_grammar([("a", DEFECTIVE, REPAIRED)])
    fired = G.localized_candidates(DEFECTIVE, grammar, function_line=3)
    assert fired and fired[0]["in_traceback_function"] is True


def test_a_candidate_never_leaves_the_tree_modified(tmp_path):
    tree = _repo(tmp_path, "r", DEFECTIVE)
    target = tree / "pkg" / "core.py"
    original = target.read_bytes()
    broken = "def total(prices)\n    return 0\n"  # not even valid Python
    outcome = G.try_candidate(tree, "pkg/core.py", "tests/test_core.py", broken)
    assert outcome["passed"] is False
    assert target.read_bytes() == original, "original bytes MUST be restored"


def test_a_real_failing_test_then_a_real_passing_fix(tmp_path):
    tree = _repo(tmp_path, "r", DEFECTIVE)
    assert G.run_test(tree, "tests/test_core.py")["passed"] is False
    fixed = G.try_candidate(tree, "pkg/core.py", "tests/test_core.py", REPAIRED)
    assert fixed["passed"] is True
    # the candidate passed AND the tree is exactly as it was: judging must never mutate the task
    assert "result -= price" in (tree / "pkg" / "core.py").read_text(encoding="utf-8")


def test_the_wrong_source_file_is_refused_rather_than_guessed(tmp_path):
    tree = _repo(tmp_path, "r", DEFECTIVE)
    task = {"repo": "x/y", "sha": "0" * 8, "name": "x", "source": "pkg/missing.py",
            "test": "tests/test_core.py", "parent_tree": str(tree)}
    row = G.solve_task(task, G.induce_grammar([("a", DEFECTIVE, REPAIRED)]))
    assert row["state"] == G.REFUSED_NO_SOURCE


def test_the_oracle_is_executed_so_expressible_means_passes(tmp_path):
    tree = _repo(tmp_path, "r", DEFECTIVE)
    verdict = G._oracle_verdict([("own", DEFECTIVE, REPAIRED)], DEFECTIVE, None, tree,
                                "pkg/core.py", "tests/test_core.py")
    assert verdict["state"] == "ORACLE_SOLVES", verdict


def test_a_traceback_frame_in_the_source_is_found_and_an_assertion_only_failure_is_not():
    stdout = ("tests/test_x.py:9: in test_x\n    pkg.core.f()\n"
              "pkg/core.py:14: in f\n    raise ValueError('x')\n")
    assert G.traceback_site(stdout, "pkg/core.py") == {"line": 14, "function": "f"}
    assert G.traceback_site("tests/test_x.py:9: AssertionError\n", "pkg/core.py") is None


def test_summarise_never_counts_a_refusal_as_solved():
    rows = [{"state": G.REFUSED_NO_TEMPLATE}, {"state": G.NOT_EXPRESSIBLE}, {"state": G.SOLVED}]
    totals = G.summarise(rows)["totals"]
    assert totals["solved"] == 1 and totals["solved_fraction"] == round(1 / 3, 4)
    assert totals["states"][G.REFUSED_NO_TEMPLATE] == 1
