#!/usr/bin/env python3
"""Tests for: a claim nothing could have refuted is not corroborated.

WHY THIS EXISTS
---------------
Round 25 measured `x*x + y` over three points being CRYSTALLISED as

    def run(x0, x1):
        return ((4.5 * x0) + (-0.5 * x1) + -0.49999999999999994)

which returns 34.5 where the truth is 120 at (10, 20). The creature had not searched badly. Three
observations exactly determine the three parameters of an affine fit, so the body has ZERO RESIDUAL ON
ZERO LEFTOVER DATA -- and `x*x + y` fits the identical three points. The crystallizer asked "does it
fit?" and accepted the answer.

That is the same defect round 25 fixed one layer down, in a different costume:

    round 25   "no candidate" was spoken without proving the SEARCH FINISHED
    here       "crystallised" is spoken without proving anything TESTED IT

WHAT THIS SUITE DEFENDS
-----------------------
The distinction itself, not any particular threshold:

    REFUTABLE       the evidence could have caught the claim being wrong
    NOT_REFUTABLE   the claim absorbed its evidence and predicted nothing beyond it
    TOO_FEW_POINTS  the evidence is structurally incapable of testing a claim this general

and the consequence: only REFUTABLE may become permanent.

The suite also records the ways this module was WRONG while it was being built, because every one of
them was a case of the instrument -- not the reasoner -- being the limit.
"""
from __future__ import annotations

import pytest

import canonical.runtime.refutability_v1 as R
import canonical.swe_kernel.meta_circular_organ_graph_v1 as M


def _mk(fn, points):
    return [(p, fn(*p)) for p in points]


# ================================================================================================
# The verdicts separate the cases they must separate
# ================================================================================================
@pytest.mark.parametrize(
    "name,fn,points",
    [
        ("square", lambda x: float(x * x), [(x,) for x in range(0, 20)]),
        ("mod_four", lambda x: float(x % 4), [(x,) for x in range(0, 8)]),
        ("table_plus_x", lambda x: [5.0, -2.0, 7.0][int(x) % 3] + x, [(x,) for x in range(1, 10)]),
        ("len_of_list", lambda xs: float(len(xs)), [([1, 2, 3],), ([4, 5],), ([6],)]),
        ("sorted_list", lambda xs: sorted(xs), [([3, 1],), ([9, 2],), ([5, 4],)]),
        ("dict_len", lambda d: float(len(d)), [({"a": 1},), ({"a": 1, "b": 2},), ({},)]),
    ],
)
def test_a_real_law_is_refutable(name, fn, points):
    """These are testable, and the test must say so or it refuses everything and buys nothing."""
    report = R.assess(_mk(fn, points))
    assert report["verdict"] == R.REFUTABLE, f"{name}: {report['verdict']} -- {report['why']}"
    assert R.may_be_permanent(report["verdict"])


def test_a_memorisation_is_not_refutable():
    """`x^3` over twenty points is outside this grammar. Any body that 'explains' it is reciting.

    This is the case that separates the module from a fit check: the body FITS, and fitting is not
    the question.
    """
    report = R.assess(_mk(lambda x: float(x ** 3), [(x,) for x in range(0, 20)]))
    assert report["verdict"] == R.NOT_REFUTABLE, report["why"]
    assert not R.may_be_permanent(report["verdict"])


def test_a_zero_degree_of_freedom_fit_is_not_testable():
    """The headline defect, in the one form where the honest answer is neither yes nor no.

    Three points cannot test an affine fit in two inputs. Reporting this as success would certify
    `x*x + y`; reporting it as failure would be wrong too, because the fit is not known to be bad.
    The module must say the evidence is incapable, which is a third thing.
    """
    for fn in (lambda x, y: x * x + y, lambda x, y: 7 * x - 2 * y + 12):
        report = R.assess(_mk(fn, [(1, 1), (3, 2), (4, 5)]))
        assert report["verdict"] == R.TOO_FEW_POINTS, report["why"]
        assert not R.may_be_permanent(report["verdict"])


def test_the_two_kinds_of_untested_are_distinguished():
    """TOO_FEW_POINTS and NOT_REFUTABLE are different facts and lead to different repairs.

    The first says BUY MORE EVIDENCE. The second says THE CLAIM ABSORBED WHAT IT HAD. Collapsing them
    is how a creature either refuses everything or believes everything.
    """
    too_few = R.assess(_mk(lambda x, y: x * x + y, [(1, 1), (3, 2), (4, 5)]))
    absorbed = R.assess(_mk(lambda x: float(x ** 3), [(x,) for x in range(0, 20)]))
    assert too_few["verdict"] != absorbed["verdict"]
    assert too_few["withheld_attempts"] == 0
    assert absorbed["withheld_attempts"] > 0


def test_no_evidence_is_not_a_pass():
    report = R.assess([])
    assert report["verdict"] == R.TOO_FEW_POINTS
    assert not R.may_be_permanent(report["verdict"])


# ================================================================================================
# Only refutable claims become permanent
# ================================================================================================
def test_an_untestable_claim_is_not_crystallised():
    """The behaviour change, at the public API. This is the defect the round exists to close."""
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((1, 1), 17), ((3, 2), 29), ((4, 5), 30)], task_signature="untestable"
    )
    assert not result["ok"], "a three-point fit with no oracle became settled knowledge"
    assert result["status"] == "PROVISIONAL_UNTESTABLE_CLAIM"
    assert result["refutability"]["verdict"] == R.TOO_FEW_POINTS
    # The proposal is still usable -- provisionality is not uselessness.
    assert result["organ"].invoke(10, 3) == 76


def test_a_claim_confirmed_by_a_purchased_prediction_is_allowed():
    """The other side of the same rule, and the reason the gate cannot be a blanket refusal.

    Door 3 asks an oracle a question the creature could not answer from its seeds. When the winner
    PREDICTS that answer correctly, the claim has been tested -- by the strongest test available --
    and refusing it would discard the one thing that actually happened.
    """
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((6, 7), 42)], task_signature="purchased", oracle=lambda p: p[0] * p[1]
    )
    assert result["ok"], result
    assert result["refutability"]["bought_predictions"] >= 1


def test_a_tested_law_is_still_crystallised():
    """No capability may be lost to this gate. Periods, tables and values are unaffected."""
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), float(x % 7)) for x in (1, 2, 3)],
        task_signature="ramp_seven",
        oracle=lambda p: float(p[0] % 7),
    )
    assert result["ok"], result["status"]
    for probe in (-90, 0, 8, 199, 260):
        assert result["organ"].invoke(float(probe)) == float(probe % 7)


# ================================================================================================
# The instrument must not be weaker than the thing it audits
# ================================================================================================
def test_the_auditor_can_see_what_the_synthesizer_can_see():
    """Recorded because it was wrong, twice, and both times it looked like a finding.

    The first version of `_fits` used only the organ graph's candidate generator (constant,
    projection, affine, table). `sorted(x)` and `len(x)` are reachable by the observational
    synthesizer and invisible to that generator, so withholding a point regenerated nothing that
    could predict it and a plainly testable law was reported NOT_REFUTABLE. An auditor narrower than
    the synthesizer certifies only what it happens to understand.
    """
    report = R.assess(_mk(lambda xs: sorted(xs), [([3, 1],), ([9, 2],), ([5, 4],)]))
    assert report["verdict"] == R.REFUTABLE, (
        "the auditor cannot reach `sorted(x)`, so it is weaker than the synthesizer it is auditing"
    )


def test_the_auditor_does_not_reject_what_the_synthesizer_accepts():
    """Two separate sandbox mismatches made a correct body look like a failure.

    `generalization_check.classify` compiles into a namespace without `sorted`; `_split_body` treats a
    leading `def run` as a helper and leaves an empty outer body. Either one alone marked
    `return sorted(x0)` as OVERFIT. The auditor now evaluates through the same exec path the
    crystallizer uses.
    """
    body = R._SynthBody("return sorted(x0)", ["x0"])
    assert R._safe_agrees(body, ([9, 2],), [2, 9])


# ================================================================================================
# DERIVED vs CHOSEN: which numbers are theorems and which are policies
# ================================================================================================
def test_the_table_requirement_declares_itself_a_policy():
    """The 4x constant was justified by a false claim, and the justification is now measured wrong.

    `table_evidence_requirement` used to say the block "must be at most a quarter of the evidence,
    which is what separates an induction from a restatement". Measured 2026-11-04: requirement `k*p`
    accepts a false table exactly when the signal was truly periodic for `T >= k` cycles, for every k
    and every p. No finite multiple removes it, so the number cannot be a separator -- it is a
    tolerance. It now reports itself as one.
    """
    import canonical.runtime.settlement_v1 as S

    policy = S.table_requirement_policy()
    assert "POLICY, NOT THEOREM" in policy["status"]
    assert policy["extra_repeats"] == S.TABLE_REPEAT_POLICY
    # The floor is the only part that is derivable: every residue seen twice means one real repeat.
    assert S.table_evidence_requirement(3) == (2 + S.TABLE_REPEAT_POLICY) * 3


def test_a_false_table_survives_every_finite_requirement():
    """The measurement that makes the constant a policy. If this ever stops holding, re-derive it."""

    def table_fits(seq, p, n):
        block = {}
        for i in range(n):
            slot = i % p
            if slot in block and abs(block[slot] - seq[i]) > 1e-9:
                return None
            block[slot] = seq[i]
        return block if len(block) == p else None

    p = 3
    for k in (2, 4, 6):
        # Truly periodic for exactly k cycles, then breaks.
        seq = [float(i % p) if i < k * p else 50.0 + i for i in range(12 * p)]
        block = table_fits(seq, p, k * p)
        assert block is not None, f"k={k}: no table induced, the premise changed"
        holds = all(abs(block[i % p] - seq[i]) < 1e-9 for i in range(k * p, len(seq)))
        assert not holds, (
            f"k={k}: a table from k cycles did NOT break -- either the construction changed or the "
            "requirement is genuinely sufficient, in which case the policy note must be revised"
        )


def test_refutability_and_the_repeat_policy_answer_different_questions():
    """They were briefly conflated, and the conflation is worth a test because it is tempting.

    refutability:  did this EVIDENCE constrain the claim?      -> yes after ONE repeat
    repeat policy: have I seen enough REPEATS to trust it?     -> a risk tolerance

    Measured: a period-3 table is REFUTABLE at n=4 (one repeat) while the same evidence would be
    refused by the 4p requirement. Both are correct; they are not the same question, and neither can
    stand in for the other.
    """
    import canonical.runtime.settlement_v1 as S

    block = [1.0, 8.0, 4.0]
    obs = [((x,), block[x % 3]) for x in range(1, 5)]
    assert R.assess(obs)["verdict"] == R.REFUTABLE, "one repeat already constrains the claim"
    assert len(obs) < S.table_evidence_requirement(3), "but it is below the repeat policy"


def test_the_probe_planner_is_not_allowed_to_beat_a_sweep_yet():
    """A recorded NEGATIVE result, guarded so it cannot be silently re-wired.

    `plan_probes` computes the deficit correctly (`arity + 2 - n`) and ranks probes by how many
    surviving pairs disagree at them, which reads as strictly better than a fixed grid. Measured
    2026-11-04: for `x // 7` over seeds 1..5 it bought probes at -1, -10, -11 -- all negative, all
    where every candidate agrees -- and never reached x >= 8 where `x // 8` and `x // 7` differ. The
    creature crystallised `x // 8`, wrong at 37, 100 and 999. The old sweep did not.

    So the decision path must keep the sweep. This test fails the moment the planner is wired back in
    without beating that measurement.
    """
    fn = lambda x: x // 7
    graph = M.MetaCircularOrganGraph(None)
    graph.growth_enabled = False
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), fn(x)) for x in range(1, 6)],
        task_signature="planner_guard",
        oracle=lambda p: fn(p[0]),
    )
    if result["ok"]:
        organ = result["organ"]
        for probe in (37, 100, 999):
            got = M._safe_eval_candidate(organ, (probe,))[1]
            assert got == fn(probe), (
                f"claimed a body wrong at {probe} ({got} vs {fn(probe)}): the probe planner is "
                "buying tests where nothing differs"
            )
    else:
        assert result["status"] in {
            "HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED",
            "CONTRADICTORY_ORACLE_OR_OUT_OF_GRAMMAR",
            "NO_CONSISTENT_HYPOTHESIS",
        }, result["status"]
