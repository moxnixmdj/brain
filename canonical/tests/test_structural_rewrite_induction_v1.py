"""Tests for structural rewrite induction by anti-unification.

The rules that carry the round:

  * encode/decode must be a faithful round trip on real ASTs, or every downstream claim is noise;
  * generalisation must create a hole exactly where two subtrees disagree, and the same hole index must be
    re-usable in the replacement;
  * matching must bind a hole consistently (one hole, one subtree) or refuse;
  * a rule enters the grammar ONLY if it reproduces its own teaching diff -- the round-trip invariant;
  * a rewrite is installed at a POSITIONAL site, so a deepcopy cannot invalidate it (this round's first defect);
  * insert/delete diffs are named, not silently re-expressed as an update rule.
"""

from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import structural_rewrite_induction_v1 as S  # noqa: E402

DEFECTIVE = "def total(prices):\n    result = 0\n    for price in prices:\n        result -= price\n    return result\n"
REPAIRED = "def total(prices):\n    result = 0\n    for price in prices:\n        result += price\n    return result\n"


def test_encode_decode_is_a_faithful_round_trip():
    for source in (DEFECTIVE, "x = [1, 2, {}]\nf(a, b=c, *d, **e)\n", "class C:\n    def m(self):\n        return 1\n"):
        tree = ast.parse(source)
        assert ast.unparse(S.decode(S.encode(tree))) == ast.unparse(tree)


def test_generalisation_puts_a_hole_exactly_where_they_disagree():
    old = ast.parse("result -= price").body[0]
    new = ast.parse("result += price").body[0]
    holes: list[dict] = []
    pattern = S.generalise(S.encode(old), S.encode(new), holes)
    assert len(holes) == 1 and holes[0]["kind"] == "atom"
    assert holes[0]["left"] == ("Sub",)
    # the same hole index is re-used in the replacement, which is what makes one rule out of two subtrees
    replacement = S.substitute(pattern, {0: holes[0]["right"]})
    assert ast.unparse(S.decode(replacement)) == "result += price"


def test_matching_binds_a_hole_consistently_or_refuses():
    holes: list[dict] = []
    pattern = S.generalise(S.encode(ast.parse("f(a)").body[0]), S.encode(ast.parse("f(b)").body[0]), holes)
    assert S.match(pattern, S.encode(ast.parse("f(zzz)").body[0])) is not None
    # the hole may bind anything, but only ONE thing per pattern: two equal occurrences must agree
    twice = S.generalise(S.encode(ast.parse("g(a, a)").body[0]), S.encode(ast.parse("g(b, b)").body[0]), holes)
    assert S.match(twice, S.encode(ast.parse("g(q, q)").body[0])) is not None
    assert S.match(twice, S.encode(ast.parse("g(q, r)").body[0])) is None


def test_the_round_trip_gate_admits_a_faithful_rule_and_rejects_a_lossy_one():
    """The gate is the round's central invariant, so it is checked on both sides directly."""
    old = ast.parse("result -= price").body[0]
    new = ast.parse("result += price").body[0]
    holes: list[dict] = []
    pattern = S.generalise(S.encode(old), S.encode(new), holes)
    replacement = S.substitute(pattern, {index: hole["right"] for index, hole in enumerate(holes)})
    faithful = S.Rule(pattern=pattern, replacement=replacement, learners=("demo",))
    assert S._round_trips(faithful, old, new) is True
    # a rule that cannot reproduce its own example may never enter the grammar
    assert S._round_trips(faithful, old, ast.parse("result *= price").body[0]) is False
    assert S.learn_rules([("demo", DEFECTIVE, REPAIRED)]), "a real operator swap must admit at least one rule"


def test_a_rewrite_installs_at_a_positional_site_and_the_source_still_parses():
    rules = S.learn_rules([("demo", DEFECTIVE, REPAIRED)])
    candidates = S.rewrite(DEFECTIVE, rules)
    assert candidates, "the learned rule must fire on the defective source"
    for entry in candidates:
        ast.parse(entry["text"])          # every candidate is a real program
        assert "+=" in entry["text"]


def test_insert_delete_is_detected_and_named_rather_than_modelled():
    added = REPAIRED.replace("    return result", "    result *= 2\n    return result")
    assert S.insert_delete_present(DEFECTIVE, added) is True
    assert S.insert_delete_present(DEFECTIVE, REPAIRED) is False


def test_the_encoding_survives_lists_which_ast_requires():
    term = S.encode(ast.parse("a = 1\nb = 2").body)
    assert term[0] == "__list__"
    assert len(S.decode(term)) == 2


def test_summarise_never_counts_a_refusal_or_the_baseline_as_a_solve():
    rows = [{"state": S.REFUSED_NO_RULE, "trials": 0, "baseline_state": "BASELINE_SOLVES"},
            {"state": S.SOLVED, "trials": 3, "baseline_state": "BASELINE_FAILS"}]
    totals = S.summarise(rows)["totals"]
    assert totals["solved"] == 1 and totals["solved_fraction"] == 0.5
    assert totals["baseline"]["BASELINE_SOLVES"] == 1


def test_headline_reports_the_baseline_on_the_same_sample():
    report = {"totals": {"tasks": 5, "solved": 0, "solved_fraction": 0.0, "solved_composite": 0, "trials": 179,
                         "states": {S.NOT_FOUND: 5}, "baseline": {"BASELINE_SOLVES": 0}}}
    line = S.headline(report)
    assert "5 real fix commits" in line and "0 solved" in line and "0 solved" in line.split("grammar on the same sample:")[1]
