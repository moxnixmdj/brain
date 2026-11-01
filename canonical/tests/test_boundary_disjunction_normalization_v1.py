"""The third hypothesis, tested where it could do damage.

`rule_scope_learning_v1` offers two scope hypotheses and notes that `SCOPE_SEMANTIC` -- same
meaning, different shape -- is absent because nothing realises it. This module realises it for
the boundary family, and the measurement that motivated it is exact: the boundary lesson reaches
**6 of 7** re-spellings with operator swaps alone, and **7 of 7** once the disjunctive form is
normalised.

A proposal source that widens applicability is dangerous in a specific way: it can rewrite
something that only *looks* like the pattern. So most of this file is refusals -- a string
literal containing `a < b or a == b` is not a disjunction, a comment is not a disjunction, and
`x < hi or x == lo` is not the identity because the operands differ.

The module has no function that applies, accepts or stores an edit, and a test pins that.
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import boundary_disjunction_normalization_v1 as norm  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402

ALGEBRAIC = "def inside7(x, hi):\n    return x < hi or x == hi\n"


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


def _renamed_rule():
    """The boundary lesson, as a plain rule dict (no store needed)."""
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    rule = cry.anti_unify_code_rule(
        "def within(x, hi):\n    return x <= hi\n",
        "def within(x, hi):\n    return x < hi\n",
        language="python",
        error_class="BOUNDARY",
    )
    assert rule is not None
    return rule


# --------------------------------------------------------------------------- the win
def test_the_disjunctive_form_is_recognised_as_the_boundary():
    forms = norm.normalize(ALGEBRAIC)
    assert len(forms) == 1
    assert forms[0]["replacement"] == "x <= hi"


def test_the_lesson_now_reaches_the_case_it_could_not():
    """6/7 before this module, 7/7 after. The patch is judged by running it."""
    rule = _renamed_rule()
    asserts = "assert inside7(10, 10) is False\nassert inside7(9, 10) is True\n"

    # The unpatched source must genuinely fail the contract, or the measurement means nothing.
    assert _execute(ALGEBRAIC, asserts) is False

    before = list(gen.propose_operator_swaps(ALGEBRAIC, rule))
    assert not any(_execute(c, asserts) for c in before), "operator swaps alone must miss it"

    after = norm.propose_semantic_swaps(ALGEBRAIC, rule, operator_swaps=gen.propose_operator_swaps)
    assert any(_execute(c, asserts) for c in after)


def test_a_renamed_twin_is_also_normalised():
    twin = "def other(p, limit):\n    return p < limit or p == limit\n"
    forms = norm.normalize(twin)
    assert forms and forms[0]["replacement"] == "p <= limit"


def test_the_reversed_order_is_recognised():
    forms = norm.normalize("def f(x, hi):\n    return x == hi or x < hi\n")
    assert forms and forms[0]["replacement"] == "x <= hi"


def test_the_greater_form_is_recognised():
    forms = norm.normalize("def f(x, lo):\n    return x > lo or x == lo\n")
    assert forms and forms[0]["replacement"] == "x >= lo"


# --------------------------------------------------------------------------- refusals
def test_different_operands_are_not_the_identity():
    """`x < hi or x == lo` is not `x <= hi`; normalising it would change meaning."""
    assert norm.normalize("def f(x, hi, lo):\n    return x < hi or x == lo\n") == []


def test_a_non_boundary_operator_pair_is_not_recognised():
    assert norm.normalize("def f(x, hi):\n    return x < hi or x != hi\n") == []
    assert norm.normalize("def f(x, hi):\n    return x < hi and x == hi\n") == []


def test_a_string_literal_is_never_rewritten():
    """The AST does not see text inside a string, so it must not be touched."""
    source = 'NOTE = "x < hi or x == hi"\n\ndef f(x, hi):\n    return x <= hi\n'
    assert norm.normalize(source) == []
    assert 'x < hi or x == hi' in source


def test_a_comment_is_never_rewritten():
    source = "def f(x, hi):\n    # x < hi or x == hi is the long way round\n    return x <= hi\n"
    assert norm.normalize(source) == []


def test_an_unrelated_disjunction_yields_nothing():
    assert norm.normalize("def f(a, b, c):\n    return a < b or b < c\n") == []


def test_an_unparseable_source_is_refused_not_guessed():
    with pytest.raises(norm.NormalizationError):
        norm.normalize("def f(:\n    return 1\n")


def test_an_empty_source_is_refused():
    with pytest.raises(norm.NormalizationError):
        norm.normalize("   ")


# --------------------------------------------------------------------------- honesty
def test_the_agreement_sample_is_labelled_as_not_a_proof():
    forms = norm.normalize(ALGEBRAIC)
    agreement = forms[0]["agreement"]
    assert agreement["agreed"] == agreement["points"]
    assert "NOT a proof" in agreement["means"]
    assert "integers" in agreement["domain"]


def test_proposals_are_bounded_and_deduplicated():
    source = "\n".join(f"def f{i}(x, hi):\n    return x < hi or x == hi\n" for i in range(60))
    forms = norm.normalize(source)
    assert len(forms) <= norm.MAX_CANDIDATES


def test_the_receipt_carries_no_authority():
    receipt = norm.explain(ALGEBRAIC)
    assert receipt["terminal_authority"] is False
    assert receipt["status"] == "NORMALISED"
    assert norm.explain("def f(a, b, c):\n    return a < b or b < c\n")["status"] == "NO_BOUNDARY_DISJUNCTION"
    assert norm.explain("def f(:")["status"] == "REFUSED"


def test_the_module_cannot_accept_anything():
    """No apply/accept/commit/store surface: it is a proposal source and nothing else."""
    public = {name for name in dir(norm) if not name.startswith("_")}
    forbidden = {"apply", "accept", "commit", "store", "save", "write", "execute"}
    assert not (public & forbidden), public & forbidden
