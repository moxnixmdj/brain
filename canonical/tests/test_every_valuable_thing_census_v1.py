"""The census must cover the WHOLE population, and must price refusals above proposals.

The law is "see every important or valuable thing: what it is and how valuable it is".
A curated list does not satisfy that. These tests pin the three properties that make the
census an answer rather than another highlight reel:

1. it enumerates every governance record and says how many it could not parse
2. its tier counts sum to the population -- no record silently dropped
3. a documented failure outranks a proposal, because a failure is evidence
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import every_valuable_thing_measured_v1 as C  # noqa: E402


def test_the_census_enumerates_the_whole_governance_population():
    out = C.census()
    on_disk = len(list((ROOT / "canonical/governance").glob("*.json")))
    assert out["total_records"] + out["parse_failures"] == on_disk


def test_every_record_lands_in_exactly_one_tier():
    out = C.census()
    assert sum(out["tier_counts"].values()) == out["total_records"]
    assert set(out["tier_counts"]) == set(C.TIER_ORDER)


def test_the_census_prices_almost_the_whole_population():
    """v1 left 34.1% unreadable. That was a classifier defect, not a tree defect."""
    out = C.census()
    unpriced = out["tier_counts"]["UNCLASSIFIED"] + out["tier_counts"]["NO_STATUS"]
    assert unpriced / out["total_records"] < 0.05, (
        f"{unpriced} of {out['total_records']} records unpriced; the classifier regressed")


def test_the_classifier_reads_the_trees_whole_vocabulary_not_one_dialect():
    """The tree writes proof as PROVED, VERIFIED, EXECUTED, DERIVED, BOUND, COMPLETE."""
    for s in ("PROVED_CURRENT_24_OF_24_PROPERTY", "VERIFIED_BOUNDED_SCOPE",
              "EXECUTED_AND_DEPLOYED", "DEDUCTIVE_CLOSURE", "EXACT_FORMAL_RESULT",
              "MINIMUM_PROOF_CARRYING_INFORMATION_DERIVED__CURRENT_COMPLETE_BASIS"):
        assert C.classify(s) == "PROVEN", s
    for s in ("FROZEN_PUBLIC_BENCHMARK_SCOPE_MAP", "STAGED_FRESH_RUN",
              "AUTHORING_TEMPLATE__COPY_AND_FILL"):
        assert C.classify(s) == "ACTIVE", s
    for s in ("TWO_CLAIM_SCOPED_EXECUTION_FAMILIES__ZERO_ROOTS_CLOSED",
              "INFRASTRUCTURE_EXECUTION_FAILURE__NO_BRAIN_BEHAVIOR_RESULT"):
        assert C.classify(s) == "REFUSED", s


def test_an_empty_status_is_its_own_tier_not_a_mystery():
    """83 records declare nothing. That needs a status written, not a vocabulary learned."""
    assert C.classify("") == "NO_STATUS"
    out = C.census()
    assert out["tier_counts"]["NO_STATUS"] > 0


def test_retraction_outranks_every_other_keyword():
    """A revoked record must never be rescued by a later PASS in the same string."""
    assert C.classify("REVOKED__PASS_RETRACTED") == "RETRACTED"
    assert C.classify("INVALIDATED_INDEPENDENT_PASS") == "RETRACTED"
    assert C.classify("SUPERSEDED_BY_V2") == "RETRACTED"


def test_refusal_outranks_proof_in_the_same_string():
    """FAIL_CLOSED_..._PASS asserts a refusal that happened to pass its own check."""
    assert C.classify("ACTIVE_FAIL_CLOSED__INDEPENDENT_PUBLIC_RUNNER_PASS") == "REFUSED"


def test_refused_outranks_candidate_in_the_pricing_order():
    """A documented failure is evidence. A proposal is not."""
    assert C.TIER_ORDER.index("REFUSED") < C.TIER_ORDER.index("CANDIDATE")


def test_the_tier_classifier_reads_status_the_way_the_records_are_written():
    assert C.classify("PASS__CLOSED_LOOP_VERIFIED") == "PROVEN"
    assert C.classify("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS") == "PROVEN"
    assert C.classify("ACTIVE_FAIL_CLOSED") == "REFUSED"
    assert C.classify("FAIL_CLOSED__EXHAUSTED") == "REFUSED"
    assert C.classify("CANDIDATE_BREAKTHROUGH") == "CANDIDATE"
    assert C.classify("REVOKED") == "RETRACTED"
    assert C.classify("ACTIVE_LIVE_ROUTE") == "ACTIVE"
    assert C.classify("") == "NO_STATUS"


def test_the_repo_actually_has_documented_failures():
    """If refusals ever hit zero, this project has stopped telling the truth about itself."""
    out = C.census()
    assert out["tier_counts"]["REFUSED"] > 0
    assert out["tier_counts"]["PROVEN"] > 0


def test_the_census_admits_what_it_does_not_prove():
    out = C.census()
    joined = " ".join(out["what_this_does_not_claim"]).lower()
    assert "only that it declares a passed check" in joined
    # the third limitation is phrased as "it is not a capability rate"
    assert "not a capability rate" in joined


def test_the_census_declares_its_denominator():
    out = C.census()
    assert out["total_records"] > 1000
    assert out["population"].startswith("canonical/governance")
