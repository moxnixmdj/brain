"""What an operator MEANS is a computation, not a membership test.

`operator_generalization_v1.GENERALIZABLE` was a frozen 16-entry list whose comment claimed its
members "mean the same thing across python/go/rust/typescript/java/cpp". Nothing in the tree computed
that claim, and it was wrong in both directions at once:

  * UNSOUND -- `%` and `/` were on the list. Executed here: `-7 % 3` is **2** in Python and **-1** in
    JavaScript and C++; `7 / 2` is 3.5 in Python and 3 for C++ integer operands. So a lesson taught in
    Python could be proposed in TypeScript and silently change what the program computes.
  * TOO NARROW -- `..=` and `..` were off it, so the shipped rust lesson
    `for i in 0..=v.len()` -> `for i in 0..v.len()`, which differs by exactly one operator token, was
    refused by an enumeration nobody derived.

The two verdicts below are NOT equally strong and every test respects that asymmetry: a `DIVERGES` is
a witnessed counterexample that nothing can argue with, while `SAME` is only a failure to refute on
one probe (`%` agrees for positive operands and disagrees for negative ones). Where no toolchain
exists the answer is `UNDECIDED` and the gate REFUSES -- an absent toolchain is never a pass.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import operator_semantics_v1 as sem  # noqa: E402

HAS_PY = bool(sem.toolchain("python"))
HAS_JS = bool(sem.toolchain("javascript"))
HAS_CXX = bool(sem.toolchain("cxx"))

needs_all = pytest.mark.skipif(
    not (HAS_PY and HAS_JS and HAS_CXX), reason="TOOLCHAIN_ABSENT__NOT_A_PASS")

# A Python lesson whose single difference is `%` -> `-`: sound inside Python, unsound in the C
# family and in JavaScript, which is exactly the pair-relative distinction a flat list cannot make.
MOD_RULE = {
    "language": "python",
    "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                       ["op", "%"], ["ws", " "], ["hole_id", "?id1"]],
    "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                           ["op", "-"], ["ws", " "], ["hole_id", "?id1"]],
}
BOUNDARY_RULE = {
    "language": "python",
    "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                       ["op", "<="], ["ws", " "], ["hole_id", "?id1"]],
    "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                           ["op", "<"], ["ws", " "], ["hole_id", "?id1"]],
}


# --------------------------------------------------------------------------- the audited claim
@needs_all
def test_the_frozen_lists_own_claim_is_refuted_by_execution():
    """Two of the list's entries are on it against the evidence of the toolchains themselves."""
    doc = sem.audit_frozen_list(sorted(gen.GENERALIZABLE))
    assert doc["authority"].startswith("NONE"), doc["authority"]
    assert "%" in doc["refuted_by_execution"]
    assert "/" in doc["refuted_by_execution"]
    # The boundary operators the list was built for are not refuted -- the audit is not a blanket
    # condemnation, it separates the entries whose claim held from the two whose claim did not.
    for op in ("<=", "<", ">=", ">", "==", "!=", "+", "-", "*"):
        row = next(r for r in doc["entries"] if r["operator"] == op)
        assert row["verdict"] != sem.DIVERGES, (op, row["observations"])


@needs_all
def test_a_divergence_is_a_witness_and_an_agreement_is_not_a_proof():
    """The asymmetry is in the output, so no caller can mistake agreement for certainty."""
    pct = sem.semantics("%")
    assert pct["verdict"] == sem.DIVERGES
    assert pct["strength"] == "WITNESSED_COUNTEREXAMPLE"
    assert pct["observations"]["python"] != pct["observations"]["javascript"]

    le = sem.semantics("<=")
    assert le["verdict"] == sem.SAME
    assert le["strength"] == "FAILURE_TO_REFUTE_ON_ONE_PROBE"
    assert le["strength"] != pct["strength"]


@needs_all
def test_bool_spelling_differences_are_not_read_as_a_divergence():
    """True / true / 1 are one answer, or the audit would refute every comparison operator."""
    obs = sem.semantics("<=")["observations"]
    assert set(obs.values()) == {"true"}, obs
    assert len(obs) == 3


# --------------------------------------------------------------------------- the gate, two-sided
def test_within_one_language_no_cross_language_claim_is_needed():
    """The gate must not block `%` everywhere -- inside Python its meaning cannot differ from itself.

    This is the control that keeps the tightening honest: a gate that refused `%` outright would look
    safe and would cost a real lesson.
    """
    r = sem.may_generalize("%", taught_in="python", proposed_in="python")
    assert r["allowed"] is True
    assert r["basis"] == "WITHIN_LANGUAGE__NO_CROSS_LANGUAGE_CLAIM_NEEDED"


@needs_all
def test_the_same_operator_has_a_different_verdict_for_each_target():
    """`/` is sound Python->JavaScript and unsound Python->Rust. A flat list cannot say this."""
    to_js = sem.may_generalize("/", taught_in="python", proposed_in="javascript")
    to_rust = sem.may_generalize("/", taught_in="python", proposed_in="rust")
    assert to_js["allowed"] is True, to_js
    assert to_rust["allowed"] is False, to_rust
    assert to_rust["basis"] == sem.DIVERGES


@needs_all
def test_a_percent_lesson_is_refused_everywhere_python_disagrees():
    for target in ("javascript", "typescript", "rust", "go"):
        r = sem.may_generalize("%", taught_in="python", proposed_in=target)
        assert r["allowed"] is False, (target, r)
        assert r["basis"] == sem.DIVERGES


def test_a_language_nothing_here_can_execute_refuses_rather_than_guesses():
    """UNDECIDED is a refusal. The old list would have allowed any of its 16 tokens into Haskell."""
    r = sem.may_generalize("<=", taught_in="python", proposed_in="haskell")
    assert r["allowed"] is False
    assert r["basis"] == sem.UNDECIDED


def test_a_probe_with_no_toolchain_reports_itself_unobserved():
    row = sem.run_probe("%", "klingon")
    assert row["ran"] is False
    assert row["verdict"] == sem.UNDECIDED


@needs_all
def test_an_alias_records_that_a_stand_in_answered():
    """TypeScript and Rust are answered by a family executable, and the verdict says so."""
    r = sem.may_generalize("%", taught_in="python", proposed_in="typescript")
    assert r.get("via_alias", {}).get("typescript") == "typescript"
    # And two names for one semantics transfer nothing at all.
    same = sem.may_generalize("%", taught_in="typescript", proposed_in="javascript")
    assert same["allowed"] is True
    assert same["basis"] == "SAME_EXECUTABLE_LANGUAGE"


def test_a_rule_that_declares_no_language_is_not_refused():
    """Most call sites pass rules with no `language`; there is no pair to compare, so nothing is lost."""
    r = sem.may_generalize("%", taught_in="", proposed_in="python")
    assert r["allowed"] is True
    assert r["basis"] == "NO_LANGUAGE_DECLARED__NOTHING_TO_COMPARE"


# --------------------------------------------------------------------------- wired into the proposer
def test_the_proposer_refuses_the_unsound_widening_but_not_the_lesson_itself():
    """Integration: the gate changes what `propose_operator_swaps` emits, in both directions."""
    py_src = "def f(a, b):\n    return a % b\n"
    ts_src = "function f(a, b) { return a % b; }\n"
    assert len(list(gen.propose_operator_swaps(py_src, MOD_RULE, language="python"))) == 1
    assert list(gen.propose_operator_swaps(ts_src, MOD_RULE, language="typescript")) == []

    gate = gen.cross_language_gate(MOD_RULE, proposed_in="typescript")
    assert gate["anything_allowed"] is False
    assert gate["refusals"] == [sem.DIVERGES]
    assert gate["allowed_swaps"] == []


@needs_all
def test_the_gate_still_widens_where_the_meaning_holds():
    """The tightening is not a wall: a boundary lesson does cross into languages that agree."""
    ts_src = "function within(x, hi) { return x <= hi; }\n"
    out = list(gen.propose_operator_swaps(ts_src, BOUNDARY_RULE, language="typescript"))
    assert out, "a lesson whose operator agrees across languages must still transfer"
    assert any("x < hi" in c for c in out), out
    assert gen.cross_language_gate(BOUNDARY_RULE, proposed_in="typescript")["anything_allowed"] is True


@needs_all
def test_explain_rule_names_the_refusal_instead_of_only_the_mismatch():
    """A refusal can now say which operator means something different over there."""
    x = gen.explain_rule(MOD_RULE, proposed_in="typescript")
    assert x["generalizable"] is True, "the structural question is unchanged and still says yes"
    assert x["cross_language"]["allowed"] is False
    assert x["cross_language"]["refusals"] == [sem.DIVERGES]
    # Omitting the target keeps the answer purely structural, as every existing caller expects.
    assert "cross_language" not in gen.explain_rule(MOD_RULE)


# --------------------------------------------------------------------------- discipline
def test_neither_module_exposes_an_acceptance_surface():
    """A gate decides what may be PROPOSED; the caller's verifier still decides what is accepted."""
    for mod in (sem, gen):
        public = {n for n in dir(mod) if not n.startswith("_")}
        assert not (public & {"apply", "accept", "commit", "store", "save"}), (mod.__name__, public)


def test_an_operator_with_no_executable_question_is_reported_not_guessed():
    doc = sem.audit_frozen_list(["~", "@"])
    assert doc["not_probed"] == ["@", "~"]
    assert doc["refuted_by_execution"] == []
