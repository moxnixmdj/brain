#!/usr/bin/env python3
"""Tests for: a refusal must teach, and the creature must grow past its own grammar.

Every test corresponds to a prediction in `PREREG_A_REFUSAL_MUST_LEARN_20261104_V1.md`, written
before the code that satisfies it.

WHY THIS ROUND EXISTS. Last round closed three doors that turned blindness into certainty, and it
worked: the creature stopped fabricating 2/10 answers. But measuring the *real* path showed it had
gained no capability at all -- all seven `x mod k` instances returned HELD_OUT_REFUTED, no organ. The
700/700 figure from that round described `synthesize_periodic_organ`, a helper **no production code
called**. The settlement layer itself was reachable only from its own tests.

So the honest summary was: honest, and impotent. A refusal that does not teach is only half a repair.
This round makes the refusal the branch point where the operator basis grows: diagnose the structure of
the evidence, then BUY the missing operator with a bounded number of questions.
"""
from __future__ import annotations

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.runtime import settlement_v1 as S


HELD_OUT = [x for x in range(-90, 0)] + [x for x in range(200, 260)]
SEEDS = (1, 2, 3)


def _real_path(k: int, *, budget: int | None = None):
    """Run the creature's REAL entry point, not a helper."""
    graph = M.MetaCircularOrganGraph(None)
    if budget is not None:
        graph.growth_evidence_budget = budget
    return graph.synthesize_or_disambiguate_skill(
        [((x,), float(x % k)) for x in SEEDS],
        task_signature=f"mod_family_{k}",
        oracle=lambda p, k=k: float(p[0] % k),
    )


def _accuracy(organ, k: int) -> tuple[int, int]:
    if organ is None:
        return 0, len(HELD_OUT)
    ok = sum(
        1
        for x in HELD_OUT
        if abs(float(M._safe_eval_candidate(organ, (x,))[1]) - float(x % k)) < 1e-9
    )
    return ok, len(HELD_OUT)


# --------------------------------------------------------------------------------------------
# P1 / P2 — the real path must reach the operator, not just the helper
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("k", [4, 5, 7, 8, 10, 11, 15])
def test_real_path_induces_the_operator_from_three_seeds(k):
    """The creature's own entry point, three seeds, no evidence table."""
    result = _real_path(k)
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED", result["status"]
    ok, total = _accuracy(result.get("organ"), k)
    assert ok == total, f"held-out {ok}/{total}"


def test_the_refusal_is_no_longer_terminal():
    """HELD_OUT_REFUTED used to end the episode. It must now be a branch point."""
    result = _real_path(7)
    assert result["ok"] is True
    assert "growth" in result
    assert result["growth"]["acquired_period"] == 7


def test_questions_spent_are_reported_and_bounded():
    """P6. The reported cost must cover what was actually asked."""
    asked = 0

    def counting_oracle(p, k=5):
        nonlocal asked
        asked += 1
        return float(p[0] % k)

    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((x,), float(x % 5)) for x in SEEDS],
        task_signature="counted",
        oracle=counting_oracle,
    )
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED"
    assert result["oracle_queries_used"] <= asked
    assert asked < 60, "the search must stay bounded"


# --------------------------------------------------------------------------------------------
# P3 — one definition of "settled", not two
# --------------------------------------------------------------------------------------------
def test_the_real_path_uses_the_settlement_layer():
    """Before this round the organ graph used only `derive_probe_space` from settlement_v1.

    `VersionSpace` and `settle` were dead code reachable only from their own tests -- two definitions
    of "settled" in one tree, only one of them exercised by the creature.
    """
    graph = M.MetaCircularOrganGraph(None)
    result = graph.synthesize_or_disambiguate_skill(
        [((6, 7), 42)],
        task_signature="billing::row_product",
        oracle=lambda xy: xy[0] * xy[1],
    )
    assert result["ok"]
    assert "settlement" in result
    assert "entropy_bits" in result["settlement"]
    assert graph.get_primary(M.SKILL, "billing::row_product") is not None


# --------------------------------------------------------------------------------------------
# P4 — diagnosis is evidence, never a name list
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "observations,expected",
    [
        ([((x,), float(x % 5)) for x in range(0, 16)], S.PERIODIC),
        ([((x,), float(x % 15)) for x in range(0, 40)], S.PERIODIC),
        ([((x,), 2.0 * x + 1) for x in range(-5, 25)], S.AFFINE),
        ([((x,), float(x * x)) for x in range(0, 12)], S.UNEXPLAINED),
        ([((x,), float(x // 7)) for x in range(0, 40)], S.UNEXPLAINED),
    ],
)
def test_diagnosis_keys_on_the_numbers(observations, expected):
    assert S.diagnose_structure(observations)["kind"] == expected


def test_a_sparse_sample_must_not_manufacture_a_period():
    """Four points at 1,2,3,-40 span 43 and agree vacuously: no two of them differ by the period.

    Sparse evidence manufacturing structure is the same defect as a sparse probe list manufacturing
    equivalence.
    """
    sparse = [((1,), 1.0), ((2,), 2.0), ((3,), 3.0), ((-40,), 0.0)]
    assert S.diagnose_structure(sparse)["kind"] == S.UNEXPLAINED


def test_a_short_linear_stretch_is_not_a_confirmed_line():
    """The first period of a cycle looks exactly like a line: 0,1,2,3,4,5 fits perfectly."""
    short = [((x,), 2.0 * x + 1) for x in range(0, 7)]
    result = S.diagnose_structure(short)
    assert result["kind"] == S.AFFINE
    assert result["provisional"] is True, "a short stretch must not be reported as confirmed"


# --------------------------------------------------------------------------------------------
# P5 — still not timid
# --------------------------------------------------------------------------------------------
def test_determined_problems_still_crystallize():
    graph = M.MetaCircularOrganGraph(None)
    product = graph.synthesize_or_disambiguate_skill(
        [((6, 7), 42)], task_signature="p", oracle=lambda xy: xy[0] * xy[1]
    )
    assert product["ok"]
    for r in range(1, 41):
        assert product["organ"].invoke(r, r + 2) == r * (r + 2)

    # AFFINE FROM THREE POINTS: the assertion below used to demand `ok`, and that expectation is
    # now wrong on the merits, not merely inconvenient. Three observations, two arguments, three
    # affine parameters -- the fit is exactly determined and has ZERO leftover data, so "it fits" is
    # arithmetic, not corroboration. Round 26 built `refutability_v1` for exactly this and the verdict
    # is TOO_FEW_POINTS (needs arity + 2 = 4).
    #
    # This test was passing before only because nothing had checked, and the file was missed from the
    # regression sweep for several rounds because the sweep list lived in /tmp. The correct assertion
    # is that the creature is CANDID about it: it refuses to call the claim corroborated, and it says
    # which verdict withheld it.
    graph2 = M.MetaCircularOrganGraph(None)
    affine = graph2.synthesize_or_disambiguate_skill(
        [((1, 1), 17), ((3, 2), 29), ((4, 5), 30)], task_signature="a"
    )
    assert not affine["ok"], "an exactly-determined fit must not be reported as corroborated"
    verdict = (affine.get("refutability") or {}).get("verdict")
    assert verdict == "TOO_FEW_POINTS", verdict

    # And with one more observation it IS settled and the answer must be exact. The law here is
    # 7*x - 2*y + 12, so at (10, 3) the value is 76 -- which is what the ORIGINAL assertion in this
    # test already said. I wrote 61 first, from careless arithmetic, and the creature was right.
    graph3 = M.MetaCircularOrganGraph(None)
    settled = graph3.synthesize_or_disambiguate_skill(
        [((1, 1), 17), ((3, 2), 29), ((4, 5), 30), ((6, 4), 46)], task_signature="a2"
    )
    assert settled["ok"], settled.get("status")
    assert settled["organ"].invoke(10, 3) == 76


# --------------------------------------------------------------------------------------------
# The bound must follow the evidence, never a constant
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("k", [20, 30])
def test_structure_beyond_the_default_budget_is_still_reachable(k):
    """A fixed evidence budget silently capped recoverable structure at its own value.

    Measured before the fix: the collection loop stopped at a hardcoded sixteen points, so a period of
    twenty was reported as a confirmed straight line and could never be recovered. The bound now
    follows the evidence's own extent.
    """
    result = _real_path(k)
    assert result["status"] == "INDUCED_OPERATOR_CRYSTALLIZED", result["status"]
    ok, total = _accuracy(result.get("organ"), k)
    assert ok == total, f"held-out {ok}/{total}"


def test_nothing_is_fabricated_for_structure_it_cannot_acquire():
    """A refusal must remain available. A creature that invents structure is worse than one that
    admits it cannot express something."""
    # `x*x` was in this list and is no longer, and that is a corrected test rather than a weakened
    # one. Measured 2026-11-04: from seeds 1..3 the creature now returns `((x0 / 1) * x0)` -- the
    # IDENTITY times x, which is exact everywhere and 0/40 wrong on held-out integers. Asserting a
    # refusal there would have been asserting that the creature is worse than it is, which is the
    # same error round 28 caught in itself.
    #
    # What must still refuse is anything the basis cannot express. `floor(x/7)` over seeds 1..3 gives
    # 0,0,0 -- one distinct output -- and the true function ramps, so a claim there is a fabrication.
    for name, fn in (("floor(x/7)", lambda v: float(v // 7)),):
        graph = M.MetaCircularOrganGraph(None)
        result = graph.synthesize_or_disambiguate_skill(
            [((x,), fn(x)) for x in SEEDS],
            task_signature=f"n_{name}",
            oracle=lambda p, fn=fn: fn(p[0]),
        )
        assert not result["ok"], f"{name} must not be crystallized as if it were understood"
        # The status set here was narrower than the refusal vocabulary, so it was testing a
        # spelling rather than the property. `UNSETTLEABLE_BY_THIS_INSTRUMENT` is a refusal with a
        # MORE informative reason -- it names the survivors and says no reachable probe separates
        # them -- and adding it does not weaken the assertion, which still requires `ok` to be False
        # and still forbids an organ.
        assert result["status"] in {
            "NO_CONSISTENT_HYPOTHESIS",
            "HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED",
            "UNDERDETERMINED_VERSION_SPACE",
            "UNSETTLEABLE_BY_THIS_INSTRUMENT",
        }, result["status"]
        assert result.get("organ") is None, "a refusal must not hand back a program"
