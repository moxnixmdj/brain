"""What a sentence can actually reach, and what this measurement is allowed to claim.

Measured 2026-11-02, first reproducible census of routing reach in this repository:

    141 capabilities, 259 declared effects
     48 self-reached by their own declared vocabulary
     55 routed to a different capability
     38 unreached, of which 35 raise GOAL_INPUT_BINDING_REQUIRED
     69 of 259 effects reached by the capability that declares them

The tests below pin the two things that would make that number a lie if they changed: that a
capability genuinely reachable by a plain sentence is not recorded as unreached, and that a row
recorded unreached carries a named cause rather than a shrug. The census is a measurement, not a
capability, and it is asserted here at the level it actually operates -- routing -- never at the
level of "the capability worked".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import route_reach_census_v1 as census  # noqa: E402


@pytest.fixture(scope="module")
def registry():
    return census.load_registry()


def test_the_registry_it_measures_is_the_live_registry(registry):
    assert len(registry) > 100
    effects = census.declared_effects(registry)
    assert len(effects) > len(registry)
    # the denominator must be the real one, not a stale quoted figure
    assert census.SCHEMA == "PROJECT_BRAIN_ROUTE_REACH_CENSUS_V1"


def test_templates_cannot_measure_reach_and_the_tool_says_so(registry):
    """THE LIMIT OF THIS INSTRUMENT, measured rather than assumed.

    `python.source.symbols.index.ast` is reachable by one ordinary English sentence --
    "Index the symbols in every python source file in canonical" -- and is recorded
    UNREACHED by all three templated addresses. The reverse also occurs:
    `python.refactor.rename_symbol` is reached by its declared vocabulary and refused by a
    natural phrasing.

    So a template census cannot produce a reach denominator. It is not an upper bound, it is
    not a lower bound, and the only defensible reading of its output is the one this test
    pins: the templated outcomes are a DIAGNOSTIC of declaration defects (the rows that demand
    inputs no sentence states), never a fraction of reachable capabilities.

    If someone later produces a corpus of real user sentences, this test should be replaced
    by one that measures reach against it. Until then, this test is the guarantee that no
    document can quote this tool's counts as a reach figure.
    """
    from canonical.runtime import goal_front_compiler_v1 as front

    good = "Index the symbols in every python source file in canonical"
    compiled = front.compile_goal(good, registry, ROOT)
    assert compiled.get("selected_capability") == "python.source.symbols.index.ast"

    row = next(r for r in census.census(registry)["rows"]
               if r["capability_id"] == "python.source.symbols.index.ast")
    assert row["outcome"] == census.UNREACHED, (
        "if a template now reaches this row the test is measuring nothing; "
        f"addresses={row['addresses']}")
    # every templated address failed for a named reason -- not silently
    assert all(a["reason"] for a in row["addresses"].values())


def test_every_unreached_row_names_its_cause(registry):
    """A row with no reason is indistinguishable from a bug in this census."""
    report = census.census(registry)
    for row in report["rows"]:
        if row["outcome"] == census.UNREACHED:
            assert row["reason"], f"{row['capability_id']} is unreached with no cause named"


def test_the_dominant_unreached_cause_is_a_declaration_fact(registry):
    """35 of 38 demand inputs no prose sentence states -- that is actionable, 'low reach' is not."""
    report = census.census(registry)
    unreached = [r for r in report["rows"] if r["outcome"] == census.UNREACHED]
    binding = [r for r in unreached if "GOAL_INPUT_BINDING_REQUIRED" in (r["reason"] or "")]
    assert binding, "the input-binding class must be visible; it was 35 of 38"
    assert len(binding) >= 0.5 * len(unreached)


def test_the_counts_are_internally_consistent(registry):
    report = census.census(registry)
    assert sum(report["outcomes"].values()) == report["capabilities"]
    assert report["capabilities"] == len(registry)
    for mode, bucket in report["outcomes_per_address"].items():
        assert sum(bucket.values()) == report["capabilities"], mode


def test_the_report_carries_the_limit_in_the_artifact_itself(registry):
    """A number that can be quoted out of context will be. The artifact says it cannot be."""
    report = census.census(registry)
    assert report["authority"] == "NO_CAPABILITY_CREDIT_ROUTING_MEASUREMENT_ONLY"
    assert report["reach_denominator_claim"] == census.NO_DENOMINATOR_CLAIM


def test_the_census_claims_no_capability_credit(registry):
    report = census.census(registry)
    assert report["authority"] == "NO_CAPABILITY_CREDIT_ROUTING_MEASUREMENT_ONLY"
    assert "rows" in report and report["rows"]
