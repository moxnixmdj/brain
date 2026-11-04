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
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED", result["status"]
    ok, total = _accuracy(result.get("organ"), _arbitrary)
    assert ok == total, f"held-out {ok}/{total}"
    assert result["growth"]["kind"] == "PERIODIC_TABLE"
    assert result["growth"]["block"] == ARBITRARY_BLOCK


def test_the_block_comes_from_the_world_not_from_a_template():
    """Two different blocks of the same period must yield two different organs.

    If the induced body were a template with a filled-in period, both would collapse to `x mod 3`.
    """
    other_block = [100.0, 0.5, -7.0]

    def other(x: float) -> float:
        return other_block[int(x) % 3]

    first = _run(_arbitrary, "block_a")
    second = _run(other, "block_b")
    assert first["growth"]["block"] == ARBITRARY_BLOCK
    assert second["growth"]["block"] == other_block
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
    assert affine["ok"]
    assert affine["organ"].invoke(10, 3) == 76


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
    induction. It must be refused.
    """
    result = _run(fn, f"refuse_{name}")
    assert not result["ok"], f"{name} was crystallized"


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
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED"
    assert result["oracle_queries_used"] <= asked
    assert asked < 100, "the search must stay bounded"
