#!/usr/bin/env python3
"""Tests for: a period is a table, not a ramp.

Corresponds to `PREREG_A_PERIOD_IS_A_TABLE_NOT_A_RAMP_20261104_V1.md`, written before the code.

WHY THIS ROUND EXISTS. Last round's headline was that the operator basis grows by induction. Re-reading
the body it emits:

    def run(x0):
        return x0 - math.floor(x0 / P) * P

`P` is filled in; the SHAPE is a template I wrote. So what was induced is one integer inside a fixed
form, and the result note's phrase "an operator that did not exist before" was too generous.

Measured consequence: a perfectly periodic function -- period 3, within-period values [5, -2, 7] --
returned NO_CONSISTENT_HYPOTHESIS, because `x mod 3` is a ramp and this function is not. The previous
round's induction could recover a ramp and nothing else while reporting success in general terms.

A period TABLE is a different object. Its block is whatever the world put there; the creature's only
contribution is the claim that the block repeats. That claim covers infinitely many inputs and any one
of them can falsify it, which is exactly what separates it from the lookup that memorised pairs and
scored 2/10 off its evidence.
"""
from __future__ import annotations

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.runtime import settlement_v1 as S


HELD_OUT = [x for x in range(-90, 0)] + [x for x in range(200, 260)]
SEEDS = (1, 2, 3)


def _run(fn, signature: str):
    graph = M.MetaCircularOrganGraph(None)
    return graph.synthesize_or_disambiguate_skill(
        [((x,), fn(x)) for x in SEEDS],
        task_signature=signature,
        oracle=lambda p: fn(p[0]),
    )


def _accuracy(organ, fn) -> tuple[int, int]:
    if organ is None:
        return 0, len(HELD_OUT)
    ok = sum(
        1
        for x in HELD_OUT
        if abs(float(M._safe_eval_candidate(organ, (x,))[1]) - fn(x)) < 1e-9
    )
    return ok, len(HELD_OUT)


# --------------------------------------------------------------------------------------------
# P1 — the function that used to be refused
# --------------------------------------------------------------------------------------------
ARBITRARY_BLOCK = [5.0, -2.0, 7.0]


def _arbitrary(x: float) -> float:
    return ARBITRARY_BLOCK[int(x) % 3]


def test_an_arbitrary_repeating_block_is_now_learned():
    """Period 3, values [5,-2,7]. Perfectly periodic; three questions determine it completely.

    The ramp-only path refused this outright, which is the whole point: it could express `x mod k` and
    nothing else while claiming to grow operators.
    """
    result = _run(_arbitrary, "arb_block")
    # Round 23: the table is now proposed by the general grammar as a PARAMETRIC node, so it is found
    # by search in the version space and reported as DISAMBIGUATED_AND_CRYSTALLIZED rather than as
    # growth. Both facts this test exists to protect are asserted below unchanged: the answers are
    # right off the evidence, and the block is the world's, not a template's.
    assert result["status"] in ("INDUCED_OPERATOR_CRYSTALLIZED", "DISAMBIGUATED_AND_CRYSTALLIZED"), result["status"]
    ok, total = _accuracy(result.get("organ"), _arbitrary)
    assert ok == total, f"held-out {ok}/{total}"
    if "growth" in result:
        assert result["growth"]["kind"] == "PERIODIC_TABLE"
        assert result["growth"]["block"] == ARBITRARY_BLOCK
    else:
        # The searched node must have solved the same block out of the same evidence.
        assert "5.0" in result["organ"].source_code and "7.0" in result["organ"].source_code


def test_the_block_comes_from_the_world_not_from_a_template():
    """Two different blocks of the same period must yield two different organs.

    If the induced body were a template with a filled-in period, both would collapse to `x mod 3`.
    """
    other_block = [100.0, 0.5, -7.0]

    def other(x: float) -> float:
        return other_block[int(x) % 3]

    first = _run(_arbitrary, "block_a")
    second = _run(other, "block_b")
    # The block lives in the emitted body either way; assert it there when growth is not the reporter.
    src_a = first["organ"].source_code
    src_b = second["organ"].source_code
    if "growth" in first:
        assert first["growth"]["block"] == ARBITRARY_BLOCK
        assert second["growth"]["block"] == other_block
    else:
        assert "100.0" in src_a or "5.0" in src_a
        assert "100.0" in src_b and "0.5" in src_b
    assert src_a != src_b, "two different blocks must not collapse to one template"
    assert first["organ"].organ_id != second["organ"].organ_id
    ok, total = _accuracy(second.get("organ"), other)
    assert ok == total


# --------------------------------------------------------------------------------------------
# P3 — a table is a hypothesis, not a memory of the evidence
# --------------------------------------------------------------------------------------------
def test_the_table_predicts_inputs_it_never_saw():
    """Evidence sits at three consecutive integers; held-out spans -90..-1 and 200..259."""
    result = _run(_arbitrary, "arb_holdout")
    organ = result["organ"]
    # inputs far outside anything observed
    assert organ.invoke(-1) == ARBITRARY_BLOCK[-1 % 3]
    assert organ.invoke(500) == ARBITRARY_BLOCK[500 % 3]
    ok, total = _accuracy(organ, _arbitrary)
    assert ok == total


# --------------------------------------------------------------------------------------------
# P2 / P5 — nothing that worked before may break
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("k", [4, 5, 7, 8, 10, 11, 15])
def test_ramps_still_work(k):
    result = _run(lambda x, k=k: float(x % k), f"ramp_{k}")
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED", result["status"]
    ok, total = _accuracy(result.get("organ"), lambda x, k=k: float(x % k))
    assert ok == total, f"held-out {ok}/{total}"


def test_determined_problems_still_crystallize():
    graph = M.MetaCircularOrganGraph(None)
    product = graph.synthesize_or_disambiguate_skill(
        [((6, 7), 42)], task_signature="p", oracle=lambda xy: xy[0] * xy[1]
    )
    assert product["ok"]
    for r in range(1, 41):
        assert product["organ"].invoke(r, r + 2) == r * (r + 2)

    graph2 = M.MetaCircularOrganGraph(None)
    affine = graph2.synthesize_or_disambiguate_skill(
        [((1, 1), 17), ((3, 2), 29), ((4, 5), 30)], task_signature="a"
    )
    # UPDATED 2026-11-04, deliberately, and this is a behaviour change rather than a repair.
    # Three points uniquely determine a two-input affine function, so this used to crystallise. It
    # no longer does, and the reason is measurable: `x*x + y` fits these same three points exactly
    # and is WRONG everywhere else (34.5 where the truth is 120 at (10, 20)). A three-parameter fit
    # to three points has zero residual on ZERO LEFTOVER DATA, so "it fits" is not corroboration --
    # any three points admit such a surface. The creature may still ANSWER with that surface; it may
    # not call it settled, because nothing tested it. What is asserted now is the honest contract:
    # a usable proposal comes back, it is correct at the probe, and it is NOT registered as settled.
    assert not affine["ok"], "a three-point fit with no oracle is not a settled law"
    assert affine["status"] == "PROVISIONAL_UNTESTABLE_CLAIM", affine["status"]
    assert affine["refutability"]["verdict"] == "TOO_FEW_POINTS"
    assert affine["organ"].invoke(10, 3) == 76, "the provisional proposal is still usable"


# --------------------------------------------------------------------------------------------
# P4 — memorisation is refused
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name,fn",
    [("x*x", lambda x: float(x * x)), ("x^3", lambda x: float(x**3))],
)
def test_non_periodic_structure_is_not_dressed_up_as_a_table(name, fn):
    """A table with one entry per observation explains the evidence by restating it.

    `x*x` over twenty points admits a "period 20" table with compression 1.0 -- a memory, not an
    induction.

    UPDATED 2026-11-04, and the original assertion was wrong. It required `not result["ok"]`, which is
    a statement about CRYSTALLISATION, while the docstring is about MEMORISATION -- the two came apart
    when the observational search stopped being starved at a 72-entry bank. `x*x` over 0..19 now
    crystallises as `(x0 / 1) * x0`: a LAWFUL body that is exact at 1000 and at -6, i.e. beyond every
    input it was shown. Refusing that would be refusing a correct answer to satisfy a test about a
    different failure. `x^3` is still refused (HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED) -- it is not
    reachable at this weight bound, and that refusal is the honest outcome, not a target.

    So the invariant asserted here is the one the docstring actually defends: whatever is claimed must
    be a RESTATEMENT-FREE body. A lookup keyed on the observations is refused; an exact law is
    allowed; and a claim that survives is checked off its evidence, where a memorisation would show.
    """
    result = _run(fn, f"refuse_{name}")
    if not result["ok"]:
        return  # refusal is always acceptable here: nothing wrong was claimed
    organ = result.get("organ")
    body = organ.source_code
    # A restatement is a literal table with an entry per observation, or a per-input branch chain.
    assert "for x0 in" not in body
    assert body.count(" if ") <= 1 and "elif" not in body, f"{name} was fitted piecewise: {body}"
    digits = sum(ch.isdigit() for ch in body)
    assert digits <= 8, f"{name} carries a literal table rather than a law: {body}"
    # And the claim must hold where it was never shown, or it is not a claim about a structure.
    for probe in (25, 37, 100, -6):
        got = organ.invoke(float(probe))
        assert abs(float(got) - fn(float(probe))) <= 1e-9, (
            f"{name} was claimed but wrong at {probe}: {got} vs {fn(float(probe))}"
        )


def test_the_table_inducer_refuses_a_restatement():
    """Directly: twenty points of x*x must not produce a twenty-entry "period"."""
    observations = [((x,), float(x * x)) for x in range(0, 20)]
    assert S.induce_periodic_table(observations) is None


# --------------------------------------------------------------------------------------------
# P6 — the compression rule is a rule, not a number that happens to work
# --------------------------------------------------------------------------------------------
def test_a_table_needs_more_evidence_than_it_contains():
    """The block must be at most a quarter of the evidence, and the requirement is queryable.

    This is what separates an induction from a restatement, and exposing it lets a caller budget for
    it instead of discovering it by failing -- which is exactly what went wrong in the first draft.
    """
    assert S.table_evidence_requirement(3) == 12
    assert S.table_evidence_requirement(10) == 40
    # three points are enough to SEE the period but not enough to CLAIM it
    three = [((x,), float(x % 3)) for x in (0, 1, 2)]
    assert S.induce_periodic_table(three) is None
    assert S.candidate_period(three) == 3, "the period is visible even when it cannot yet be claimed"
    twelve = [((x,), float(x % 3)) for x in range(0, 12)]
    assert S.induce_periodic_table(twelve) is not None


def test_long_periods_are_reachable_so_the_rule_is_not_a_ceiling():
    """Fixing `provisional` at 16 last round capped recoverable structure at period 16.

    The rule here scales with the period, so a long period costs more evidence rather than becoming
    impossible.
    """
    for k in (30, 44):
        result = _run(lambda x, k=k: float(x % k), f"long_{k}")
        assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED", (k, result["status"])
        ok, total = _accuracy(result.get("organ"), lambda x, k=k: float(x % k))
        assert ok == total, f"k={k} held-out {ok}/{total}"


# --------------------------------------------------------------------------------------------
# Regressions found and fixed inside this round, kept as tests
# --------------------------------------------------------------------------------------------
def test_collected_evidence_is_never_self_contradictory():
    """A duplicate probe appended with a different value destroys every hypothesis downstream.

    Measured: anchoring the probe on a fixed seed while incrementing a counter produced
    (2, 5.0) followed by (2, 7.0). Contradictory evidence looks exactly like "no structure here",
    which is the most expensive misdiagnosis available.
    """
    seen: dict[tuple, float] = {}

    def recording_oracle(p):
        value = _arbitrary(p[0])
        if p in seen:
            assert seen[p] == value, f"probe {p} asked twice with different answers"
        seen[p] = value
        return value

    graph = M.MetaCircularOrganGraph(None)
    graph.synthesize_or_disambiguate_skill(
        [((x,), _arbitrary(x)) for x in SEEDS],
        task_signature="no_contradiction",
        oracle=recording_oracle,
    )
    assert seen


def test_the_reported_cost_covers_the_questions_actually_asked():
    asked = 0

    def counting_oracle(p):
        nonlocal asked
        asked += 1
        return _arbitrary(p[0])

    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), _arbitrary(x)) for x in SEEDS],
        task_signature="costed",
        oracle=counting_oracle,
    )
    assert result["status"] in ("INDUCED_OPERATOR_CRYSTALLIZED", "DISAMBIGUATED_AND_CRYSTALLIZED")
    assert result["oracle_queries_used"] <= asked
    assert asked < 100, "the search must stay bounded"
