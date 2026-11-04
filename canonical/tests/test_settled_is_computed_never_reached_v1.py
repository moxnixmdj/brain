#!/usr/bin/env python3
"""Tests for the settlement layer and for operator induction from evidence.

Every test here corresponds to a prediction stated in
`PREREG_SETTLED_IS_COMPUTED_NEVER_REACHED_20261104_V1.md`, written before the code that satisfies it.

The defect under test is not "a table was wrong". It is that the creature decided a question was
*settled* from the path it had taken instead of from the evidence it held, through three doors:

  door 1  its probe grid could not separate two programs, and it read that as them being the same;
  door 2  a remembered organ agreed with the examples already given, and it never asked whether it
          was right;
  door 3  its grammar could only think of one program, and it read that as the world being determined.

Measured consequence before the repair: experience made held-out accuracy WORSE (2/10 -> 0/10 on the
same instance) while every status string reported success. A creature that gets faster at being wrong
is the exact opposite of one that becomes smarter.
"""
from __future__ import annotations

import math

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.runtime import settlement_v1 as S


HELD_OUT = [x for x in range(-60, 0)] + [x for x in range(100, 140)]


def _accuracy(organ, fn) -> tuple[int, int]:
    if organ is None:
        return 0, len(HELD_OUT)
    ok = 0
    for x in HELD_OUT:
        good, val = M._safe_eval_candidate(organ, (x,))
        if good and abs(float(val) - float(fn(x))) < 1e-9:
            ok += 1
    return ok, len(HELD_OUT)


def _mod_space(ks):
    return S.VersionSpace(
        [S.Hypothesis(key=k, predict=lambda p, k=k: float(p[0] % k)) for k in ks]
    )


# --------------------------------------------------------------------------------------------
# P3 / P6 — the settlement layer refuses to convert blindness into certainty
# --------------------------------------------------------------------------------------------
def test_identical_functions_are_reported_unsettleable_never_settled():
    """Two different programs computing the same function: no probe can ever separate them.

    The correct report is that the instrument is blind, not that one of them is right.
    """
    space = S.VersionSpace([
        S.Hypothesis(key="x2", predict=lambda p: float(p[0]) * 2),
        S.Hypothesis(key="x_plus_x", predict=lambda p: float(p[0]) + float(p[0])),
    ])
    result = S.settle(
        space,
        domain=[(x,) for x in range(1, 11)],
        probes=S.derive_probe_space([((1,), 2.0)]),
        oracle=lambda p: float(p[0]) * 2,
    )
    assert result.status == S.UNSETTLEABLE_BY_THIS_INSTRUMENT
    assert not result.settled
    assert result.queries_used == 0


def test_evidence_outside_the_hypothesis_space_is_named_not_blamed_on_the_world():
    """The old code returned CONTRADICTORY_ORACLE_OR_OUT_OF_GRAMMAR, blaming the world.

    `x % 15` is perfectly consistent; it simply was not expressible. Those are different facts and
    must be reported differently.
    """
    space = _mod_space((2, 3, 4, 5, 6, 7))
    result = S.settle(
        space,
        domain=[(x,) for x in range(1, 11)],
        probes=S.derive_probe_space([((1,), 1.0), ((2,), 2.0), ((3,), 3.0)]),
        oracle=lambda p: float(p[0] % 15),
    )
    assert result.status == S.EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE


def test_missing_oracle_is_its_own_status():
    space = _mod_space((2, 3, 4, 5))
    result = S.settle(
        space,
        domain=[(x,) for x in range(1, 11)],
        probes=S.derive_probe_space([((1,), 1.0)]),
        oracle=None,
    )
    assert result.status == S.NO_ORACLE


# --------------------------------------------------------------------------------------------
# P6 — the cost gate is load-bearing
# --------------------------------------------------------------------------------------------
def test_a_probe_that_costs_more_than_it_buys_is_declined():
    space = _mod_space((2, 3, 4, 5, 6, 7))
    result = S.settle(
        space,
        domain=[(x,) for x in range(1, 11)],
        probes=S.derive_probe_space([((1,), 1.0)]),
        oracle=lambda p: float(p[0] % 5),
        probe_cost_bits=999.0,
    )
    assert result.status == S.INSTRUMENT_TOO_COSTLY
    assert result.queries_used == 0


# --------------------------------------------------------------------------------------------
# The information primitive must be exact, and must not depend on a remembered alphabet
# --------------------------------------------------------------------------------------------
def test_information_gain_equals_exact_mutual_information():
    space = _mod_space((2, 3, 4, 5, 6, 7))
    probes = S.derive_probe_space([((1,), 1.0)])
    post = space.posterior()
    h0 = -sum(v * math.log2(v) for v in post.values() if v > 0)
    worst = 0.0
    for probe in probes:
        classes: dict[float, list[float]] = {}
        for k, mass in post.items():
            classes.setdefault(float(probe[0] % k), []).append(mass)
        expected = 0.0
        for masses in classes.values():
            pc = sum(masses)
            expected += pc * (-sum((m / pc) * math.log2(m / pc) for m in masses))
        worst = max(worst, abs((h0 - expected) - space.information_gain(probe)))
    assert worst < 1e-9


def test_information_gain_does_not_require_the_outcome_to_have_been_seen_before():
    """First draft scored probes against an alphabet drawn from past observations.

    A probe whose every outcome was new then scored zero and was declared unlearnable -- the very
    blindness this module exists to expose. A probe's worth must depend only on how it splits.
    """
    space = S.VersionSpace([
        S.Hypothesis(key="a", predict=lambda p: float(p[0]) + 1000.0),
        S.Hypothesis(key="b", predict=lambda p: float(p[0]) - 1000.0),
    ])
    # No observations at all: both outcomes are entirely novel.
    assert space.information_gain((7,)) == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------------------------------------------
# P1 / P2 — experience must not make the creature worse, and must not be merely cosmetic
# --------------------------------------------------------------------------------------------
def test_experience_can_be_worse_and_now_reports_it():
    """The measured regression: recall of `x mod 4` for `x mod 5` cost 0 queries and scored 0/10.

    After the repair the recalled organ must be refuted by asking, so warm is never worse than cold.
    """
    graph = M.MetaCircularOrganGraph(None)

    def call(k):
        examples = [((x,), float(x % k)) for x in (1, 2, 3)]
        return graph.synthesize_or_disambiguate_skill(
            examples, task_signature="mod_family", oracle=lambda p, k=k: float(p[0] % k)
        )

    cold_graph = M.MetaCircularOrganGraph(None)
    cold = []
    for k in (4, 5, 7):
        r = cold_graph.synthesize_or_disambiguate_skill(
            [((x,), float(x % k)) for x in (1, 2, 3)],
            task_signature="mod_family",
            oracle=lambda p, k=k: float(p[0] % k),
        )
        cold.append(_accuracy(r.get("organ"), lambda x, k=k: x % k))

    warm = []
    for k in (4, 5, 7):
        r = call(k)
        warm.append(_accuracy(r.get("organ"), lambda x, k=k: x % k))

    for (cok, _), (wok, _) in zip(cold, warm):
        assert wok >= cok, "experience made the creature less accurate, which is the defect"


# --------------------------------------------------------------------------------------------
# P3 — door 1: a grid that cannot separate must not produce a verdict
# --------------------------------------------------------------------------------------------
def test_single_surviving_hypothesis_is_not_automatically_crystallized():
    """Door 3: `x mod 5` from seeds 1..3 yields only `if x0 <= 0: 0/x0 else x0/1` -- the identity.

    It matches the seeds and was admitted with zero questions at 0/10 held-out. A grammar's poverty
    cannot certify a program, so the winner must predict something it has not already been shown.
    """
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), float(x % 5)) for x in (1, 2, 3)],
        task_signature="mod_family",
        oracle=lambda p: float(p[0] % 5),
    )
    # The identity function must never be the answer. Two acceptable outcomes, both honest:
    #   * INDUCED_OPERATOR_CRYSTALLIZED -- the refusal became a question and bought the real operator;
    #   * HELD_OUT_REFUTED_*            -- no structure could be acquired, so it refuses.
    # What is NOT acceptable, and is what this test exists to prevent, is `proj_0` / the identity being
    # crystallized because the grammar could think of only one thing.
    assert result["status"] in {"INDUCED_OPERATOR_CRYSTALLIZED"} or result["status"].startswith(
        "HELD_OUT_REFUTED"
    )
    organ = result.get("organ")
    if organ is not None:
        wrong = [x for x in range(-40, 0, 3) if organ.invoke(x) == x]
        assert not wrong, "the identity function was crystallized as the answer"


def test_ambiguity_that_is_inconsequential_still_crystallizes():
    """`2x+2` and `2*(x+1)` are the same function by different structure.

    Refusing between them would be timidity dressed as rigour (P5): the choice has no consequence on
    any input, so it is not a guess.
    """
    graph = M.MetaCircularOrganGraph(None)
    inc = M.make_organ(
        stratum=M.SKILL, name="inc", task_signature="op::inc", entrypoint="run",
        source_code="def run(x0):\n    return x0 + 1\n",
    )
    dbl = M.make_organ(
        stratum=M.SKILL, name="dbl", task_signature="op::dbl", entrypoint="run",
        source_code="def run(x0):\n    return 2 * x0\n",
    )
    graph.register_organ(inc)
    graph.register_organ(dbl)
    result = graph.synthesize_or_disambiguate_skill(
        [((3,), 8), ((5,), 12), ((0,), 2), ((-3,), -4)],
        task_signature="op::double_inc",
    )
    assert result["ok"], result
    assert result["organ"].invoke(10) == 22


# --------------------------------------------------------------------------------------------
# P4 / P5 — the world is not blamed, and the creature is not timid
# --------------------------------------------------------------------------------------------
def test_determined_problems_still_crystallize():
    """P5. A creature that refuses everything is trivially never wrong and perfectly useless."""
    graph = M.MetaCircularOrganGraph(None)
    product = graph.synthesize_or_disambiguate_skill(
        [((6, 7), 42)], task_signature="billing::row_product", oracle=lambda xy: xy[0] * xy[1]
    )
    assert product["ok"]
    organ = product["organ"]
    for r in range(1, 41):
        assert organ.invoke(r, r + 2) == r * (r + 2)

    graph2 = M.MetaCircularOrganGraph(None)
    affine = graph2.synthesize_or_disambiguate_skill(
        [((1, 1), 17), ((3, 2), 29), ((4, 5), 30)], task_signature="custom::lin_novel"
    )
    assert affine["ok"]
    assert affine["organ"].invoke(10, 3) == 7 * 10 - 2 * 3 + 12


# --------------------------------------------------------------------------------------------
# The operator basis grows: an operator that was never in the grammar is INDUCED from evidence
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("k", [4, 5, 7, 8, 10, 11, 15])
def test_periodicity_is_induced_and_generalises_off_the_evidence(k):
    """`%` is not in the organ grammar at all; every claim of solving this family was a lookup.

    The period is induced from observed periodicity, which is what `Omega_{t+1} = Omega_t U P_t U C_t`
    claims the creature does. Held-out inputs include negatives, which the evidence deliberately
    does not contain.
    """
    examples = [((x,), float(x % k)) for x in range(0, 2 * k + 4)]
    got = M.synthesize_periodic_organ(
        examples, task_signature=f"mod_{k}", oracle=lambda p, k=k: float(p[0] % k)
    )
    assert got is not None, f"no periodic operator induced for k={k}"
    organ, found = got
    assert found["period"] == k
    ok, total = _accuracy(organ, lambda x, k=k: x % k)
    assert ok == total, f"held-out {ok}/{total} for k={k}"


def test_two_remainder_conventions_are_told_apart_by_one_question():
    """`math.fmod(-3, 7)` is -3 while `%` gives 4. All-positive evidence cannot distinguish them.

    Measured: 30/30 correct above zero and 6/30 below. Assuming either is guessing; one question
    settles it. This is the frozen-menu lesson one layer up -- a convention is a hypothesis.
    """
    k = 5
    examples = [((x,), float(x % k)) for x in range(0, 2 * k + 4)]  # no negatives
    organ, found = M.synthesize_periodic_organ(
        examples, task_signature="mod_conv", oracle=lambda p: float(p[0] % k)
    )
    assert found["convention_settled"] is True
    assert found["convention_queries"] >= 1
    assert "floor" in organ.name
    ok, total = _accuracy(organ, lambda x: x % k)
    assert ok == total


def test_without_an_oracle_an_unsettled_convention_is_declared_not_assumed():
    k = 5
    examples = [((x,), float(x % k)) for x in range(0, 2 * k + 4)]
    organ, found = M.synthesize_periodic_organ(examples, task_signature="mod_conv2")
    assert found["convention_settled"] is False
    assert "convention_unsettled_because" in found


def test_period_induction_declines_when_the_evidence_is_not_periodic():
    """`floor(x/3)` is not periodic. Inducing a period anyway would be the lookup defect again."""
    examples = [((x,), float(math.floor(x / 3))) for x in range(0, 40)]
    assert M.induce_periodic_operator(examples) is None


def test_induction_cost_tracks_structure_size_not_experience():
    """Honest limit, measured: the minimum evidence to induce period p is ~2p+2.

    Learning `mod 5` does NOT make `mod 15` cheap. What experience buys is the operator's existence.
    Stating this as a test keeps a future round from quietly claiming compounding that is not there.
    """
    needed = {}
    for k in (3, 5, 9):
        n = None
        for sample in range(4, 200):
            found = M.induce_periodic_operator([((x,), float(x % k)) for x in range(sample)])
            if found is not None and found["period"] == k:
                n = sample
                break
        needed[k] = n
    assert all(v is not None for v in needed.values())
    assert needed[3] < needed[5] < needed[9], needed


# --------------------------------------------------------------------------------------------
# P2 — compounding that is real: a settled convention is remembered, and stays falsifiable
# --------------------------------------------------------------------------------------------
def test_a_settled_convention_makes_later_instances_cost_nothing():
    """Seven instances of one family, ONE question in total, 700/700 held-out.

    This is the honest form of compounding. The old version of compounding cut queries too -- from 12
    to 1 -- while accuracy fell to 0/10. The difference is not the number, it is that this one buys
    correctness instead of spending it.
    """
    memory = M.ConventionMemory()
    total_queries = 0
    for k in (4, 5, 7, 8, 10, 11, 15):
        examples = [((x,), float(x % k)) for x in range(0, 2 * k + 4)]
        organ, found = M.synthesize_periodic_organ(
            examples, task_signature=f"m{k}", oracle=lambda p, k=k: float(p[0] % k), memory=memory
        )
        total_queries += found.get("convention_queries", 0)
        ok, total = _accuracy(organ, lambda x, k=k: x % k)
        assert ok == total, f"k={k} held-out {ok}/{total}"
    assert total_queries == 1, f"expected one question for the whole family, used {total_queries}"
    assert memory.settled and memory.convention == "floor"


def test_a_learned_convention_can_be_overturned_by_evidence():
    """A belief that cannot be revised is a frozen table that took a longer route into the tree."""
    memory = M.ConventionMemory()
    memory.observe("fmod")  # a stale belief from an earlier life
    assert memory.settled
    examples = [((x,), float(x % 5)) for x in range(-14, 14)]  # only the floor convention fits
    organ, found = M.synthesize_periodic_organ(
        examples, task_signature="overturn", oracle=None, memory=memory
    )
    assert memory.refuted == 1
    assert memory.convention == "floor"
    assert "floor" in organ.name
    ok, total = _accuracy(organ, lambda x: x % 5)
    assert ok == total
