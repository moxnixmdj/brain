"""One lesson must reach every spelling of itself, and must never reach anything else.

Measured 2026-11-01, one boundary lesson (`<= hi` -> `< hi`) taught and offered seven
structurally novel Python instances: it reached **1 of 7**, because the stored pattern was
`return ?id0 <= ?id1` and a rule taught inside a `return` can only fire inside a `return`.

`operator_generalization_v1` recovers the general form: the lesson IS a single operator swap,
and that swap has three closed forms (direct, operands swapped, negated). Every case below is
judged by executing the patched source against its own contract, never by string comparison.

The refusals matter more than the wins. This module widens applicability, so it must refuse
anything that is not exactly one operator difference, and must never rewrite inside a string
or a comment.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

TAUGHT_BEFORE = "def within(x, hi):\n    return x <= hi\n"
TAUGHT_AFTER = "def within(x, hi):\n    return x < hi\n"


def _execute(source: str, asserts: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(source, "<cand>", "exec"), ns)
    except Exception:
        return False
    try:
        exec(compile(asserts, "<asserts>", "exec"), ns)
    except Exception:
        return False
    return True


def _twin_oracle(source: str) -> bool:
    """Name-agnostic: the twin is alpha-renamed, so find the callable, do not name it."""
    ns: dict = {}
    try:
        exec(compile(source, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


@pytest.fixture()
def rule(tmp_path):
    store = cry.VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet=TAUGHT_BEFORE, after_snippet=TAUGHT_AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=_twin_oracle,
    )
    assert taught["crystallized"] is True
    rules = store.lookup_rules("python", "BOUNDARY")
    assert len(rules) == 1
    return rules[0]


def _solved(source: str, asserts: str, rule) -> bool:
    return any(_execute(c, asserts) for c in gen.propose_operator_swaps(source, rule))


# --------------------------------------------------------------------------- the win
CASES = [
    ("operator inside a larger expression",
     "def ok(x, hi):\n    return (x >= 0) and (x <= hi)\n",
     "assert ok(0, 10) is True\nassert ok(10, 10) is False\nassert ok(-1, 10) is False\n"),
    ("operator inside an if-statement",
     "def ok2(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
     "assert ok2(0, 10) is True\nassert ok2(10, 10) is False\n"),
    ("operator in a while guard",
     "def count(n, hi):\n    i = n\n    c = 0\n    while i <= hi:\n        c += 1\n        i += 1\n    return c\n",
     "assert count(0, 10) == 10\nassert count(0, 0) == 0\n"),
    ("operands swapped (hi >= x)",
     "def inside4(x, hi):\n    return hi >= x\n",
     "assert inside4(10, 10) is False\nassert inside4(9, 10) is True\n"),
    ("negated form not (x > hi)",
     "def inside6(x, hi):\n    return not (x > hi)\n",
     "assert inside6(10, 10) is False\nassert inside6(9, 10) is True\n"),
]


@pytest.mark.parametrize("label,source,asserts", CASES)
def test_the_lesson_reaches_a_new_spelling_of_itself(rule, label, source, asserts):
    assert _solved(source, asserts, rule), f"missed: {label}"


def test_an_algebraic_rewrite_is_not_an_operator_swap(rule):
    """`x < hi or x == hi` -> `x < hi` is simplification, not the taught lesson. Recorded as
    a genuine miss rather than folded into a claim."""
    source = "def inside7(x, hi):\n    return x < hi or x == hi\n"
    asserts = "assert inside7(10, 10) is False\nassert inside7(9, 10) is True\n"
    assert _solved(source, asserts, rule) is False


# --------------------------------------------------------------------------- the refusals
def test_a_string_literal_is_never_rewritten(rule):
    source = "def f(x, hi):\n    note = 'x <= hi'\n    return x < hi\n"
    for candidate in gen.propose_operator_swaps(source, rule):
        assert "note = 'x < hi'" not in candidate


def test_a_comment_is_never_rewritten(rule):
    source = "def f(x, hi):\n    # x <= hi\n    return x < hi\n"
    for candidate in gen.propose_operator_swaps(source, rule):
        assert "# x < hi" not in candidate


def test_a_rule_with_two_differences_is_refused():
    rule = {
        "pattern_tokens": [["op", "<="], ["ws", " "], ["hole_id", "?a"]],
        "replacement_tokens": [["op", "<"], ["ws", " "], ["hole_id", "?a"]],
    }
    assert gen.explain_rule(rule)["generalizable"] is True

    two_diffs = {
        "pattern_tokens": [["op", "<="], ["ws", " "], ["hole_id", "?a"]],
        "replacement_tokens": [["op", ">"], ["ws", " "], ["hole_id", "?b"]],
    }
    assert gen.explain_rule(two_diffs)["generalizable"] is False


def test_a_non_operator_difference_is_refused():
    rule = {
        "pattern_tokens": [["kw", "return"], ["ws", " "], ["op", "<="]],
        "replacement_tokens": [["kw", "yield"], ["ws", " "], ["op", "<="]],
    }
    assert gen.derive_operator_swap(rule) is None
    assert gen.derive_swap_family(rule) == []


def test_an_empty_rule_proposes_nothing():
    assert list(gen.propose_operator_swaps("x = 1\n", {})) == []


def test_the_swap_family_is_the_three_closed_forms(rule):
    family = gen.derive_swap_family(rule)
    assert {"from": "<=", "to": "<"} in family
    assert {"from": ">=", "to": ">"} in family
    assert {"from": ">", "to": ">="} in family


def test_every_candidate_changes_exactly_one_occurrence(rule):
    source = "def f(a, b, c, d):\n    return a <= b and c <= d\n"
    seen = list(gen.propose_operator_swaps(source, rule))
    assert seen, "expected at least one proposal"
    for candidate in seen:
        # exactly one `<=` became `<`: one fewer `<=`, one character shorter, and the other
        # occurrence plus the surrounding `and` must be untouched.
        assert candidate.count("<=") == source.count("<=") - 1
        assert len(candidate) == len(source) - 1
        assert " and " in candidate


def test_proposals_are_bounded(rule):
    source = "def f(xs):\n    return " + " and ".join(f"xs[{i}] <= 9" for i in range(200)) + "\n"
    got = list(gen.propose_operator_swaps(source, rule))
    assert len(got) <= gen.MAX_CANDIDATES


def test_the_module_cannot_accept_anything():
    """There is no accept/commit entry point: only proposals. The caller verifies."""
    names = {n for n in dir(gen) if not n.startswith("_")}
    assert "accept" not in names and "commit" not in names and "apply" not in names
