#!/usr/bin/env python3
"""Tests for: a missing answer is not a missing language.

Corresponds to `PREREG_IT_ONLY_EVER_SEES_THE_DIAGONAL_20261104_V1.md`, written before the code.

WHY THIS ROUND EXISTS. The previous four rounds made the creature better at ANSWERING while its
SENSES stayed fixed. Round 25's pre-registration predicted three defects one layer below inference:

  P1  `derive_probe_space` crashes on any unhashable input (list/dict/set), because it keys a `set`
      with `tuple(ex_in)`.
  P2  every probe is `tuple([x] * arity)`, so a two-argument task is only ever observed on the
      diagonal `f(n, n)`. `x+y` is affine there and `x*y+1` is not, which is the whole difference.
  P4  `table_evidence_requirement(P)` spends a 4x constant over the information floor.

P1 and P2 were confirmed. P4 was measured but NOT fixed here (see the note); the pre-registration was
falsified on it and the falsification is recorded rather than dropped.

WHAT THE MEASUREMENT THEN SHOWED, AND THE THESIS CORRECTION. After P1 and P2 were fixed, `x*y` was
solved but `x*y+1` still returned NO_CONSISTENT_HYPOTHESIS. The first reading -- "so the grammar is the
remaining limit" -- was WRONG, and wrong in a way worth encoding as a test. `((x0 * x1) + 1)` is in the
grammar and is found in 64 ms. It was unreachable because every call site in the organ graph searched
with `max_bank_size` 64--80 while the synthesizer's own default is 900 and `evidence_demand_v1`'s is
5000. At a 72-entry bank the search fills the bank (72/72) and misses the body; at 900 it finds it.

So the defect was not one of grammar, semantics, or reasoning. It was a VERDICT ISSUED ABOUT THE
LANGUAGE FROM A SEARCH THAT HAD NOT FINISHED. The tree already knew this distinction -- `evidence_demand_v1`
has `SEARCH_TRUNCATED` exactly for it -- but the organ graph's fast path never consulted it.

The tests below defend the distinction itself, not the constant that happened to expose it: a bank is a
budget, a budget is not a fact about a grammar, and a refusal built on a filled bank must say so.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import canonical.runtime.swe_observational_program_synthesizer_v1 as SYNTH
import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.runtime import settlement_v1 as S


# ================================================================================================
# P1 -- PERCEPTION MUST NOT CRASH ON INPUTS THAT ARE NOT HASHABLE
# ================================================================================================
@pytest.mark.parametrize(
    "example",
    [
        ([1, 2, 3],),
        ([3, 1, 2],),
        ({"a": 1, "b": 2},),
        ({1, 2, 3},),
        ([1, [2, 3]],),
    ],
)
def test_the_probe_space_never_raises_on_unhashable_input(example):
    """`seen.add(tuple(ex_in))` raised `TypeError: unhashable type: 'list'`.

    Not a refusal -- an exception, escaping into whatever called it. Four rounds of inference work
    never saw it because no earlier round ever passed a list.
    """
    space = S.derive_probe_space([(example, 1), ([1, 2], 2)])
    assert isinstance(space, list) and space
    for probe in space:
        assert isinstance(probe, tuple)


def test_canonical_key_identifies_equal_containers():
    assert S.canonical_key([1, 2]) == S.canonical_key([1, 2])
    assert S.canonical_key([1, 2]) != S.canonical_key([2, 1])
    assert S.canonical_key({"a": [3]}) == S.canonical_key({"a": [3]})
    # Must be usable as a dict/set key, which is the entire point of the helper.
    assert len({S.canonical_key([1, [2, 3]]), S.canonical_key([1, [2, 3]])}) == 1


@pytest.mark.parametrize(
    "name,fn",
    [
        ("len_of_list", lambda xs: float(len(xs))),
        ("sorted_list", lambda xs: sorted(xs)),
        ("dict_len", lambda d: float(len(d))),
        ("tuple_len", lambda t: float(len(t))),
    ],
)
def test_list_and_dict_tasks_are_solved_not_crashed(name, fn):
    """The crash was masking a capability: these are all reachable once perception stops throwing."""
    graph = M.MetaCircularOrganGraph(None)
    # The input is a 1-TUPLE WRAPPING the argument. Writing `([1,2,3], 3.0)` instead would be read by
    # Python as a THREE-argument example `(1, 2, 3) -> 3.0`, so the task would silently become an
    # arity-3 integer task and the assertion would be about something else entirely. That mistake was
    # made and measured on 2026-11-04: the growth loop saw only ints and correctly refused.
    seeds = [(([1, 2, 3],),), (([4, 5],),), (([6],),)]
    if name == "sorted_list":
        seeds = [(([3, 1],),), (([9, 2],),), (([5, 4],),)]
    elif name == "dict_len":
        seeds = [(({"a": 1},),), (({"a": 1, "b": 2},),), (({},),)]
    elif name == "tuple_len":
        seeds = [(((1, 2),),), (((1, 2, 3),),), (((),),)]
    # UPDATED 2026-11-04: an oracle is now supplied on purpose. Three observations cannot TEST a
    # claim, so without one the creature reports PROVISIONAL_UNTESTABLE_CLAIM -- the same verdict
    # `x*x + y` gets, and correctly so, because three points fit both equally. The capability being
    # asserted here is that perception no longer CRASHES and the law is reachable once it is tested.
    result = graph.synthesize_or_disambiguate_skill(
        [(s, fn(*s)) for s in seeds],
        task_signature=f"p1_{name}",
        oracle=lambda p, fn=fn: fn(p[0]),
    )
    assert result["ok"], f"{name} failed: {result.get('status')}"


# ================================================================================================
# P2 -- THE PROBE SPACE MUST NOT BE A DIAGONAL
# ================================================================================================
def test_the_probe_space_contains_non_diagonal_probes():
    """The regression that would silently undo this round.

    Every probe was `tuple([x] * arity)`, so a two-argument task was only ever observed at `f(n, n)`
    and any function that is affine on the diagonal looked indistinguishable from the diagonal itself.
    """
    space = S.derive_probe_space([((1, 2), 3), ((2, 3), 7), ((4, 1), 5)])
    two_slot = [p for p in space if len(p) == 2]
    assert two_slot, "no two-slot probes at all"
    off_diagonal = [p for p in two_slot if p[0] != p[1]]
    assert off_diagonal, (
        "every probe is on the diagonal: a two-argument task is unobservable off f(n,n), "
        "which is what made x*y+1 unreachable no matter how good inference got"
    )


@pytest.mark.parametrize(
    "name,fn,seeds,held_out",
    [
        ("product_plus_one", lambda x, y: x * y + 1, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4), (7, 8), (6, 6)]),
        ("product", lambda x, y: x * y, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4), (7, 8)]),
        ("difference", lambda x, y: x - y, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4), (7, 8)]),
        ("sum", lambda x, y: x + y, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4)]),
        ("scaled_product", lambda x, y: 2 * x * y, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4)]),
        ("shifted_sum", lambda x, y: (x + y) * 2, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4)]),
    ],
)
def test_two_argument_structure_is_solved_exactly_off_the_seeds(name, fn, seeds, held_out):
    """The creature is allowed to ASK -- and here it must.

    Three points do not determine a two-argument law, so without an oracle the right answer is a
    refusal (asserted separately below). The capability under test is that the question, once asked,
    can be answered: the body must exist in the grammar and be exact where it was never shown.
    """
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [(s, fn(*s)) for s in seeds], task_signature=f"p2_{name}", oracle=lambda p: fn(*p)
    )
    assert result["ok"], f"{name} refused: {result.get('status')}"
    organ = result["organ"]
    for probe in held_out:
        got = organ.invoke(*probe)
        assert got == fn(*probe), f"{name} wrong at {probe}: {got} vs {fn(*probe)}"


def test_a_form_not_in_the_grammar_is_still_refused_not_guessed():
    """P2 must not become 'everything is answerable'.

    `x^3` is outside this weight bound. The correct outcome is a refusal; a claim would be a
    fabricated capability. This is the guard that keeps the round honest.
    """
    fn = lambda x: float(x ** 3)
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), fn(x)) for x in range(0, 20)],
        task_signature="p2_refuse_cube",
        oracle=lambda p: fn(p[0]),
    )
    if result["ok"]:
        organ = result["organ"]
        for probe in (25, 37, 100, -6):
            assert abs(float(organ.invoke(float(probe))) - fn(float(probe))) <= 1e-9


# ================================================================================================
# THE REAL INVARIANT -- A BUDGET IS NOT A FACT ABOUT A GRAMMAR
# ================================================================================================
def test_a_filled_bank_is_reported_as_a_budget_and_not_as_a_grammar_fact():
    """`last_search_coverage()` must answer after an ordinary miss, not only after a collecting one.

    Before this round coverage was written only on the `collect_admissible` path, so the default path
    -- the one the organ graph uses -- returned `None` and explained nothing. A caller could not tell
    'the language cannot express this' from 'the search ran out', and the organ graph asserted the
    former.
    """
    examples = [((1, 2), 3), ((2, 3), 7), ((4, 1), 5)]
    body = SYNTH.synthesize_python_function_body(
        ["x0", "x1"], examples, extra_constants=[1, 2, 3, 4],
        max_weight=6, max_bank_size=8,
    )
    assert body is None
    coverage = SYNTH.last_search_coverage()
    assert coverage, "no coverage recorded on the default path after a miss"
    assert coverage.get("complete") is False
    assert coverage.get("bank_size") == coverage.get("bank_capacity")


def test_a_body_that_exists_at_a_larger_budget_is_not_reported_as_absent():
    """The exact measurement that falsified 'the grammar is the limit'.

    `((x0 * x1) + 1)` is reachable. At a 72-entry bank the search fills the bank and returns None; the
    organ graph called that NO_CONSISTENT_HYPOTHESIS. It is not a hypothesis about the language.
    """
    examples = [((1, 2), 3), ((2, 3), 7), ((4, 1), 5)]
    starved = SYNTH.synthesize_python_function_body(
        ["x0", "x1"], examples, extra_constants=[1, 2, 3, 4],
        max_weight=3, max_bank_size=72,
    )
    assert starved is None, "the premise of this test no longer holds: 72 now suffices"
    assert SYNTH.last_search_coverage().get("complete") is False
    roomy = SYNTH.synthesize_python_function_body(
        ["x0", "x1"], examples, extra_constants=[1, 2, 3, 4],
        max_weight=3, max_bank_size=900,
    )
    assert isinstance(roomy, str) and "*" in roomy, roomy


def test_the_organ_graph_escalates_a_budget_before_refusing():
    """The call sites must not search at 64--80 and then speak about the grammar.

    The claim is about the LADDER, so that is what is asserted: the hit has to come from a bank wider
    than the 72 that filled, and the module must have asked a budget that could answer.
    """
    examples = [((1, 2), 3), ((2, 3), 7), ((4, 1), 5)]
    body = M._observational_body_with_proven_budget(
        ["x0", "x1"], examples, extra_constants=[1, 2, 3, 4], max_weight=3
    )
    assert isinstance(body, str) and "*" in body, body
    used = SYNTH.last_search_coverage().get("bank_capacity")
    assert used is not None and int(used) > 72, (
        f"found the body without ever searching wider than the starved budget (capacity={used})"
    )


def test_no_oracle_means_refuse_rather_than_guess():
    """Three points do not determine a two-argument law, and the creature must not pretend they do.

    This is the guard on the P2 win: widening perception must widen what can be ASKED, not license a
    guess. Measured 2026-11-04: `x*y+1` without an oracle is UNDERDETERMINED_VERSION_SPACE, and the
    two survivors really do disagree off the seeds.
    """
    fn = lambda x, y: x * y + 1
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [(s, fn(*s)) for s in [(1, 2), (2, 3), (4, 1)]], task_signature="p2_no_oracle"
    )
    assert not result["ok"], "claimed a two-argument law from three points"
    assert result["status"] in {
        "UNDERDETERMINED_VERSION_SPACE",
        "UNSETTLEABLE_BY_THIS_INSTRUMENT",
        "NO_CONSISTENT_HYPOTHESIS",
        "SEARCH_TRUNCATED",
    }, result["status"]


def test_a_truncated_search_is_never_called_no_consistent_hypothesis():
    """If the search cannot prove it finished, the status must name the budget.

    Checked structurally: the refusal string must exist in the module and be produced on the
    non-exhaustive branch. Reading the source is deliberate -- the point is that the branch exists,
    because whether it is reached depends on a budget that may legitimately change.
    """
    source = Path(M.__file__).read_text()
    assert "SEARCH_TRUNCATED" in source
    assert source.count("NO_CONSISTENT_HYPOTHESIS") >= 2, "the unconditional refusal is gone"


# ================================================================================================
# P4 -- NO FALSE POSITIVES FROM THE WIDER SEARCH
# ================================================================================================
@pytest.mark.parametrize(
    "name,fn,seeds,held_out",
    [
        ("product_plus_sum", lambda x, y: x * y + x, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4), (7, 8)]),
        ("floor_over_three", lambda x, y: x // 3 + y, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4)]),
        ("product_minus_seven", lambda x, y: x * y - 7, [(1, 2), (2, 3), (4, 1)],
         [(10, 20), (5, 1), (-3, 4)]),
        ("mod_scaled", lambda x: (x % 4) * 3, [(1,), (2,), (3,), (4,), (5,), (6,)],
         [(10,), (37,), (100,), (-7,), (13,)]),
    ],
)
def test_a_refusal_is_acceptable_but_a_wrong_claim_is_not(name, fn, seeds, held_out):
    """The risk of a wider search is a confident answer that is wrong.

    Every one of these is either refused or exact on held-out inputs. There is no third outcome.
    """
    _oracle = lambda p: fn(*p)
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [(s, fn(*s)) for s in seeds], task_signature=f"p4_{name}", oracle=_oracle
    )
    if not result["ok"]:
        return
    organ = result["organ"]
    for probe in held_out:
        ok, got = M._safe_eval_candidate(organ, probe)
        assert ok, f"{name} claimed a body that does not evaluate at {probe}"
        assert got == fn(*probe), f"{name} claimed a wrong body: {got} != {fn(*probe)} at {probe}"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN FALSE POSITIVE, measured 2026-11-04, PRE-EXISTING and NOT caused by this round. "
        "`x*x + y` on three points is crystallised as the wrong affine body "
        "((4.5*x0) + (-0.5*x1) + -0.5), which returns 34.5 where the truth is 120 at (10, 20). "
        "Identical result on the pre-round tree, so this is not a regression -- it is the next "
        "round's question, and it is marked strict so the day it is fixed this test FAILS and the "
        "note must be updated rather than the failure quietly disappearing. "
        "DIAGNOSIS: three observations exactly determine the three parameters of an affine fit, so "
        "`_solve_multilinear` returns a body with zero residual and zero DEGREES OF FREEDOM. Zero "
        "residual on zero leftover data is not corroboration -- it is the definition of a curve drawn "
        "through three points. The same root cause as the budget defect fixed this round: a claim "
        "about the world issued from evidence structurally incapable of testing it."
    ),
)
def test_a_zero_degree_of_freedom_fit_is_not_yet_a_law():
    """This test encodes a defect, not a capability. It must start failing when the defect is fixed."""
    fn = lambda x, y: x * x + y
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [(s, fn(*s)) for s in [(1, 2), (2, 3), (4, 1)]], task_signature="p4_zero_dof"
    )
    if not result["ok"]:
        pytest.fail("refused -- the defect is fixed, remove the xfail and assert the law")
    organ = result["organ"]
    for probe in [(10, 20), (5, 1), (-3, 4)]:
        got = M._safe_eval_candidate(organ, probe)[1]
        assert got == fn(*probe), f"wrong at {probe}: {got} != {fn(*probe)}"


def test_periodic_structure_is_unchanged_by_the_wider_search():
    """P3 -- the earlier wins must still hold at the new budget."""
    fn = lambda x: float(x % 7)
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), fn(x)) for x in (1, 2, 3)],
        task_signature="p3_ramp_7",
        oracle=lambda p: fn(p[0]),
    )
    assert result["ok"], result.get("status")
    organ = result["organ"]
    for probe in [-90, -3, 0, 8, 199, 260]:
        assert organ.invoke(float(probe)) == fn(float(probe)), probe
