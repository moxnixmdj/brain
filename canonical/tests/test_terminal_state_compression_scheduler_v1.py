from canonical.runtime.terminal_state_compression_scheduler_v1 import (
    classify_probability_state,
    makespan_bound,
    robust_state_compression_priority,
    verify_shadow_reality_lease,
)


def _base_shadow_receipt():
    return {
        "generic_isolation_kernel_pass": True,
        "benchmark_thin_adapter_pass": True,
        "candidate_frozen": True,
        "executor_independent": True,
        "executed_hashes_equal_precommit": True,
        "outputs_bound_to_precommit": True,
        "outputs_escrowed": True,
        "outputs_hidden_from_candidate": True,
        "unrelated_work_cannot_mutate_candidate": True,
        "zero_incremental_spend_guard": True,
        "route_result_not_used_for_acceptance_before_fixed_point": True,
        "acceptance_credit_before_fixed_point": False,
        "promotion_before_fixed_point": False,
        "candidate_can_read_shadow_outputs": False,
    }


def test_unknown_probability_is_preserved():
    assert classify_probability_state() == "UNKNOWN__NO_POINT_ESTIMATE"
    assert classify_probability_state(
        deterministic_entailment=True
    ) == "ONE"
    assert classify_probability_state(
        falsified_until_wake=True
    ) == "ZERO_UNTIL_MATERIAL_WAKE"


def test_decisive_probe_gets_positive_priority_without_success_probability():
    score = robust_state_compression_priority(
        guaranteed_progress=0,
        guaranteed_deletion=1,
        guaranteed_information=1,
        critical_path_seconds=2,
    )
    assert score == 1.0


def test_correlation_penalty_lowers_priority():
    a = robust_state_compression_priority(
        guaranteed_progress=1,
        guaranteed_deletion=1,
        guaranteed_information=1,
        critical_path_seconds=3,
        correlation_penalty=0,
    )
    b = robust_state_compression_priority(
        guaranteed_progress=1,
        guaranteed_deletion=1,
        guaranteed_information=1,
        critical_path_seconds=3,
        correlation_penalty=1,
    )
    assert b < a


def test_shadow_collection_fails_closed_without_separate_authority():
    r = _base_shadow_receipt()
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is False
    assert "explicit_shadow_reality_authority" in out["missing"]
    assert out["acceptance_credit_authorized"] is False


def test_shadow_collection_ready_only_with_all_premises_and_authority():
    r = _base_shadow_receipt()
    r["explicit_shadow_reality_authority"] = True
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is True
    assert out["missing"] == []
    assert out["fresh_reality_authority_granted_by_this_module"] is False


def test_candidate_feedback_path_blocks_shadow_collection():
    r = _base_shadow_receipt()
    r["explicit_shadow_reality_authority"] = True
    r["candidate_can_read_shadow_outputs"] = True
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is False


def test_overlap_bound_is_never_worse_than_serial():
    out = makespan_bound(120, 80)
    assert out["serial_seconds"] == 200
    assert out["overlapped_lower_bound_seconds"] == 120
    assert out["maximum_structural_seconds_saved"] == 80
