"""The probe range was deciding the verdict, and a check that finds the whole class.

Pre-registration: `PREREG_PROBE_RANGE_DECIDES_THE_VERDICT_20261104_V1.md`.

Two results here, in order of importance:

1. The **eighth instance** of this project's recurring defect, and the first found by a *check*
   rather than by hand. `demand_evidence` decided "same explanation" by comparing behaviour over a
   frozen 21-value probe list that runs from -5 to 20 while omitting 8, 9, 11 and 13..19. Two
   admissible bodies for `mod 2` disagree at **x = 14** -- inside the stated range, simply never
   sampled -- and were reported as one explanation.

2. `audit_frozen_dimensions` generalises the test: for each frozen dimension in the decision path,
   recompute with that dimension widened and report whether the answer MOVED. That is what turns
   "find instance nine by staring at a table" into "ask the machine which tables are load-bearing".
"""
from __future__ import annotations

import pytest

from canonical.runtime.evidence_demand_v1 import (
    DETERMINED,
    DISAMBIGUATING_PROBES,
    FROZEN_DIMENSIONS,
    audit_frozen_dimensions,
    behaviour_signature,
    demand_evidence,
    disclose_probes,
    group_by_behaviour,
)


def _line(fn, xs=range(1, 6)):
    return [((x,), float(fn(x))) for x in xs]


# ------------------------------------------------------------------------------------------------
# P1: a verdict flips on real data
# ------------------------------------------------------------------------------------------------

def test_the_frozen_probe_list_merges_bodies_that_disagree_on_an_unsampled_input():
    """The concrete lie, stated without needing the search to reproduce it.

    Two piecewise bodies, both admissible for `x % 2` on 1..9. They agree at 20 of the frozen 21
    probes and disagree at x = 14, which the frozen list never samples.
    """
    a = "if x % 2 == 0:\n    return (0 / x)\nreturn abs((1 / -1))"
    b = ("if ((100 % x) == 2):\n    return abs((1 / -1))\n"
         "elif x % 2 == 0:\n    return (0 / x)\nreturn abs((1 / -1))")

    frozen_same = behaviour_signature(a, ["x"], DISAMBIGUATING_PROBES) == \
        behaviour_signature(b, ["x"], DISAMBIGUATING_PROBES)
    assert frozen_same, "the frozen range must be blind to this pair, or the test proves nothing"
    assert 14 not in DISAMBIGUATING_PROBES
    assert 14 in disclose_probes([b], [])

    disclosed_same = behaviour_signature(a, ["x"], disclose_probes([a, b], [])) == \
        behaviour_signature(b, ["x"], disclose_probes([a, b], []))
    assert not disclosed_same, "disclosed probes must separate bodies that differ at x = 14"


def test_the_explanation_count_moves_on_real_datasets():
    """P1: `mod 2` is 6 explanations under the frozen list and more once probes are disclosed."""
    examples = _line(lambda x: x % 2, range(1, 10))
    report = demand_evidence(["x"], examples)
    disclosure = report["probe_disclosure"]
    assert disclosure["groups_frozen"] < disclosure["groups_disclosed"]
    assert disclosure["split_by_disclosure"] >= 1


@pytest.mark.parametrize("fn,name,domain", [
    (lambda x: 2 * x, "2x", range(1, 6)),
    (lambda x: x * x, "x*x", range(1, 6)),
    # `mod 2` over 1..5 does NOT over-merge (frozen 16 == disclosed 16); the over-merge appears over
    # 1..9. Recorded per-domain because the whole point is that the defect is a property of the
    # probe list AND the data, and stating only the function would hide that.
    (lambda x: x % 2, "mod2", range(1, 10)),
])
def test_every_over_merging_case_is_now_caught(fn, name, domain):
    report = demand_evidence(["x"], _line(fn, domain))
    assert report["probe_disclosure"]["split_by_disclosure"] >= 1, name


def test_the_defect_is_a_property_of_probes_and_data_together():
    """`mod 2` over 1..5 does not over-merge; over 1..9 it does. Neither fact alone explains it."""
    narrow = demand_evidence(["x"], _line(lambda x: x % 2, range(1, 6)))["probe_disclosure"]
    wide = demand_evidence(["x"], _line(lambda x: x % 2, range(1, 10)))["probe_disclosure"]
    assert narrow["split_by_disclosure"] == 0
    assert wide["split_by_disclosure"] >= 1


# ------------------------------------------------------------------------------------------------
# P2: disclosure can only split, never merge -- so it can only ever reduce overconfidence
# ------------------------------------------------------------------------------------------------

def test_disclosure_never_merges_groups():
    """P2: a larger probe set cannot make two bodies agree that disagreed. Monotone by definition."""
    for fn in (lambda x: 2 * x, lambda x: 3 * x + 1, lambda x: max(0, x), lambda x: x % 2):
        examples = _line(fn, range(-3, 4))
        report = demand_evidence(["x"], examples)
        disclosure = report["probe_disclosure"]
        assert disclosure["groups_disclosed"] >= disclosure["groups_frozen"], (
            "disclosure merged groups, which is impossible unless the grouping is unstable")


# ------------------------------------------------------------------------------------------------
# P3: the repair does not disturb a correct verdict
# ------------------------------------------------------------------------------------------------

def test_a_genuine_determination_survives_the_repair():
    """P3/F2: `3x+1` is one explanation for a real reason, and must stay that way.

    Trading a false DETERMINED for a false PROVISIONAL is not progress. If this ever fails, the
    disclosure is splitting bodies that genuinely agree over the derived range, and the derived
    range is too fine.
    """
    report = demand_evidence(["x"], _line(lambda x: 3 * x + 1))
    assert report["status"] == DETERMINED
    assert report["explanation_count"] == 1
    assert report["probe_disclosure"]["split_by_disclosure"] == 0


# ------------------------------------------------------------------------------------------------
# P4: the check generalises past the probe range
# ------------------------------------------------------------------------------------------------

def test_the_audit_covers_every_frozen_dimension_in_the_decision_path():
    """P4: the deliverable. Not a fixed table, but a question asked of every frozen dimension."""
    audit = audit_frozen_dimensions(["x"], _line(lambda x: 2 * x))
    assert set(audit["dimensions"]) == set(FROZEN_DIMENSIONS)
    assert audit["frozen_dimensions"] == list(FROZEN_DIMENSIONS)


def test_the_audit_finds_the_probe_range_load_bearing():
    """The check must rediscover, without being told, the defect this round was about."""
    audit = audit_frozen_dimensions(["x"], _line(lambda x: x % 2, range(1, 10)))
    assert "probe_range" in audit["load_bearing"]


def test_the_audit_finds_the_constant_alphabet_load_bearing():
    """It must also rediscover LAST round's defect: `3x+1` needs a constant outside the menu."""
    audit = audit_frozen_dimensions(["x"], _line(lambda x: 3 * x + 1))
    assert "constant_alphabet" in audit["load_bearing"]


def test_the_audit_reports_a_stable_dimension_without_claiming_soundness():
    """`stable` means "did not move", never "proven correct". The wording has to carry that."""
    audit = audit_frozen_dimensions(["x"], _line(lambda x: 2 * x))
    assert audit["authority"] == "NONE"
    assert "not a proof of soundness" in audit["why"] or "not only about the data" in audit["why"]


# ------------------------------------------------------------------------------------------------
# P5: it will not catch everything, and says so
# ------------------------------------------------------------------------------------------------

def test_the_report_still_says_over_the_probe_range_not_that_functions_are_equal():
    """P5/F4: no finite sampling decides functional equality.

    A report that stopped saying "verified over the probe range" and started saying "these are the
    same explanation" would be WORSE than the bug, because it would launder a sampling result into a
    claim about functions.
    """
    report = demand_evidence(["x"], _line(lambda x: 3 * x + 1))
    assert "probe range" in report["why"]
    basis = report["probe_disclosure"]["basis"]
    assert "AUDIT" in basis or "audit" in basis
    assert "not a proof" in basis or "no finite sampling" in basis


def test_the_disclosure_record_states_what_the_frozen_range_had_merged():
    """A number that was wrong must be reported alongside its correction, not silently replaced."""
    report = demand_evidence(["x"], _line(lambda x: x % 2, range(1, 10)))
    disclosure = report["probe_disclosure"]
    assert disclosure["groups_frozen"] == 6
    assert disclosure["groups_disclosed"] == report["explanation_count"]
