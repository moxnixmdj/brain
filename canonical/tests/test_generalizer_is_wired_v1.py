"""The generaliser must be reachable from the live repair loop.

`operator_generalization_v1` implements the correction this project needed: a stored rule
that differs by one operator token is a lesson about that operator, and it applies wherever
the operator appears -- not only inside the statement skeleton it was taught from.

Measured 2026-11-09 on 774 jinja functions:
    narrow crystallised matcher : 0 proposals  (0.00%)
    operator_generalization     : 764 proposals (98.71%)

That reach is worthless if the closed-loop solver never calls it. It did not: the candidate
generator called only `crystallizer.iter_crystallized_code_rule_candidates`. These tests pin
the wire, and pin the honest interpretation of the number (proposal reach, not a solve rate).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as E  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as OG  # noqa: E402


def test_the_solver_imports_the_generaliser():
    src = Path(E.__file__).read_text()
    assert "operator_generalization_v1" in src
    assert "propose_operator_swaps" in src


def test_the_candidate_generator_can_emit_an_operator_generalized_candidate():
    """A stored rule that is one operator apart must produce a bounded, valid candidate."""
    rule = {
        "skill_id": "test_rule_0001",
        "language": "python",
        "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?a"],
                           ["ws", " "], ["op", "<="], ["ws", " "], ["hole_id", "?b"]],
        "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?a"],
                               ["ws", " "], ["op", "<"], ["ws", " "], ["hole_id", "?b"]],
    }
    src = "def f(a, b):\n    if a <= b:\n        return a\n    return b\n"
    cands = list(OG.propose_operator_swaps(src, rule, language="python", limit=4))
    assert cands, "generaliser produced nothing for a pure operator lesson"
    assert any("a < b" in c for c in cands)
    assert all(c != src for c in cands)


def test_the_generaliser_refuses_a_rule_that_is_not_one_operator_apart():
    """Anything that is not a single-operator difference is a guess, and must be refused."""
    rule = {
        "skill_id": "test_rule_0002",
        "language": "python",
        "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?a"]],
        "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?b"],
                               ["ws", " "], ["op", "+"], ["ws", " "], ["num", "1"]],
    }
    assert OG.derive_operator_swap(rule) is None
    assert list(OG.propose_operator_swaps("x = a\n", rule, language="python")) == []


def test_the_generaliser_never_substitutes_inside_a_string_literal():
    rule = {
        "skill_id": "test_rule_0003",
        "language": "python",
        "pattern_tokens": [["hole_id", "?a"], ["ws", " "], ["op", "+"], ["ws", " "],
                           ["hole_num", "?n"]],
        "replacement_tokens": [["hole_id", "?a"], ["ws", " "], ["op", "-"], ["ws", " "],
                               ["hole_num", "?n"]],
    }
    src = 'msg = "a + b"\n'
    out = list(OG.propose_operator_swaps(src, rule, language="python", limit=8))
    assert all('"a + b"' in c for c in out), "an operator inside a string was rewritten"


def test_the_reach_number_is_recorded_as_reach_and_not_as_a_solve_rate():
    import json
    rec = ROOT / "canonical/governance/WEB_CONFIRMS_THE_TREE_HEDGED_20261109_V1.json"
    d = json.loads(rec.read_text())
    m = d["what_the_held_modules_actually_do__measured_today"]["operator_generalization_v1"]
    assert m["measurement_today_jinja_774_functions"]["generalised_proposals"].endswith("(98.71%)")
    assert "not a solve rate" in m["honest_reading"]
