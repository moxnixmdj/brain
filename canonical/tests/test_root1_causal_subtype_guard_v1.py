#!/usr/bin/env python3
import pytest

from canonical.runtime.root1_causal_subtype_guard_v1 import (
    Root1CausalSubtypeError,
    classify_root1_causal_subtype,
    livebench_v6_current_projection,
)


def test_livebench_current_projection_is_route_gap_not_underlying_capability():
    out = livebench_v6_current_projection()
    assert out["status"] == "ROOT1_OPERATIVE_ROUTE_GAP_ONLY"
    assert out["causal_subtype"] == "OPERATIVE_ROUTE_OR_COMPOSITION_GAP"
    assert out["integration_repair_authorized"] is True
    assert out["underlying_capability_acquisition_authorized"] is False
    assert out["counts"] == {
        "observed_case_count": 72,
        "valid_candidate_response_count": 0,
        "policy_block_count": 43,
        "runtime_or_composition_failure_count": 29,
        "independently_adjudicated_semantic_failure_count": 0,
    }


def test_valid_independently_adjudicated_semantic_failure_can_authorize_acquisition():
    out = classify_root1_causal_subtype({
        "positive_operational_gap": True,
        "operative_failure_demonstrated": True,
        "observed_case_count": 10,
        "valid_candidate_response_count": 10,
        "policy_block_count": 0,
        "runtime_or_composition_failure_count": 0,
        "independently_adjudicated_semantic_failure_count": 3,
        "underlying_behavior_exercised": True,
        "independent_semantic_acceptance": True,
        "execution_surface_verified_ready": True,
        "failure_attributed_to_underlying_behavior": True,
    })
    assert out["status"] == "ROOT1_UNDERLYING_CAPABILITY_GAP_ESTABLISHED"
    assert out["underlying_capability_acquisition_authorized"] is True
    assert out["integration_repair_authorized"] is False


def test_semantic_failure_without_causal_gates_fails_closed():
    out = classify_root1_causal_subtype({
        "positive_operational_gap": True,
        "operative_failure_demonstrated": True,
        "observed_case_count": 5,
        "valid_candidate_response_count": 5,
        "policy_block_count": 0,
        "runtime_or_composition_failure_count": 0,
        "independently_adjudicated_semantic_failure_count": 1,
    })
    assert out["status"] == "ROOT1_SUBTYPE_UNPROVED_FAIL_CLOSED"
    assert out["underlying_capability_acquisition_authorized"] is False
    assert out["integration_repair_authorized"] is False


def test_no_positive_operational_gap_means_no_action():
    out = classify_root1_causal_subtype({
        "positive_operational_gap": False,
        "operative_failure_demonstrated": True,
    })
    assert out["root1_operational_gap"] is False
    assert out["underlying_capability_acquisition_authorized"] is False


def test_counts_must_be_consistent():
    with pytest.raises(
        Root1CausalSubtypeError,
        match="COUNTS_EXCEED_OBSERVED_CASE_COUNT",
    ):
        classify_root1_causal_subtype({
            "positive_operational_gap": True,
            "operative_failure_demonstrated": True,
            "observed_case_count": 3,
            "valid_candidate_response_count": 1,
            "policy_block_count": 2,
            "runtime_or_composition_failure_count": 1,
        })


def test_semantic_failures_cannot_exceed_valid_responses():
    with pytest.raises(
        Root1CausalSubtypeError,
        match="SEMANTIC_FAILURES_EXCEED_VALID_RESPONSES",
    ):
        classify_root1_causal_subtype({
            "positive_operational_gap": True,
            "operative_failure_demonstrated": True,
            "observed_case_count": 4,
            "valid_candidate_response_count": 1,
            "policy_block_count": 3,
            "runtime_or_composition_failure_count": 0,
            "independently_adjudicated_semantic_failure_count": 2,
        })
