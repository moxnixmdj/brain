from canonical.runtime.generic_precommit_isolation_theorem_v1 import commitment_digest
from canonical.runtime.terminal_state_compression_scheduler_v1 import (
    classify_probability_state,
    makespan_bound,
    robust_state_compression_priority,
    verify_shadow_execution_result,
    verify_shadow_reality_lease,
)


def _isolation_receipt():
    r = {}
    for i, c in enumerate(
        ("candidate", "harness", "scorer", "environment", "policy"), start=1
    ):
        r[f"{c}_sha256"] = str(i) * 64
        r[f"observed_{c}_sha256"] = str(i) * 64
    r.update(
        {
            "commit_event_sequence": 10,
            "case_reveal_event_sequence": 11,
            "execution_start_event_sequence": 12,
            "independent_executor": True,
            "committed_components_immutable": True,
            "no_case_or_evaluation_feedback_to_committed_components": True,
            "unrelated_work_cannot_mutate_committed_components": True,
            "outputs_bound_to_commitment": True,
            "observed_causal_edges": [
                ["case_content", "execution_output"],
                ["evaluation_output", "receipt_store"],
            ],
        }
    )
    r["commitment_sha256"] = commitment_digest(r)
    return r


def _adapter():
    return {
        "population_identity_verified": True,
        "scorer_or_grader_equivalence_verified": True,
        "effort_and_context_semantics_verified": True,
        "tool_and_environment_boundary_verified": True,
        "exact_comparator_identity_verified": True,
        "no_proxy_substitution_verified": True,
        "zero_incremental_spend_or_entitlement_verified": True,
        "acceptance_rule_bound": True,
    }


def _lease():
    return {
        "isolation_receipt": _isolation_receipt(),
        "benchmark_adapter": _adapter(),
        "candidate_frozen": True,
        "outputs_bound_to_precommit": True,
        "outputs_escrowed": True,
        "outputs_hidden_from_candidate": True,
        "outputs_hidden_from_optimizer_until_release": True,
        "outputs_hidden_from_candidate_mutators_until_release": True,
        "unrelated_work_cannot_mutate_candidate": True,
        "zero_incremental_spend_guard": True,
        "route_result_not_used_for_acceptance_before_fixed_point": True,
        "release_requires_zero_reality_fixed_point": True,
        "release_requires_independent_verification": True,
        "one_use_lease": True,
        "shadow_authority_receipt_content_addressed": True,
        "explicit_shadow_reality_authority": True,
        "shadow_authority_receipt_sha256": "a" * 64,
        "lease_nonce_sha256": "b" * 64,
        "lease_id": "shadow:livebench-if:v1",
        "benchmark_id": "LIVEBENCH_IF_GE_65_7",
        "escrow_sink_id": "escrow:terminal:v1",
        "lease_consumed": False,
        "execution_ordinal": 0,
        "acceptance_credit_before_fixed_point": False,
        "promotion_before_fixed_point": False,
        "candidate_can_read_shadow_outputs": False,
        "optimizer_can_read_shadow_outputs_before_release": False,
    }


def test_unknown_probability_is_preserved():
    assert classify_probability_state() == "UNKNOWN__NO_POINT_ESTIMATE"
    assert classify_probability_state(deterministic_entailment=True) == "ONE"
    assert (
        classify_probability_state(falsified_until_wake=True)
        == "ZERO_UNTIL_MATERIAL_WAKE"
    )


def test_decisive_probe_gets_priority_without_success_probability():
    assert robust_state_compression_priority(
        guaranteed_progress=0,
        guaranteed_deletion=1,
        guaranteed_information=1,
        critical_path_seconds=2,
    ) == 1.0


def test_shadow_lease_rechecks_underlying_isolation_and_adapter():
    out = verify_shadow_reality_lease(_lease())
    assert out["shadow_collection_ready"] is True
    assert out["generic_isolation_kernel_pass"] is True
    assert out["benchmark_thin_adapter_pass"] is True
    assert out["shadow_collection_authority_granted_by_this_module"] is False


def test_boolean_self_assertion_cannot_substitute_for_underlying_receipts():
    r = _lease()
    r.pop("isolation_receipt")
    r["generic_isolation_kernel_pass"] = True
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is False
    assert "MISSING_ISOLATION_RECEIPT" in out["reasons"]


def test_optimizer_visibility_blocks_shadow_collection():
    r = _lease()
    r["optimizer_can_read_shadow_outputs_before_release"] = True
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is False


def test_shadow_collection_fails_closed_without_separate_authority():
    r = _lease()
    r["explicit_shadow_reality_authority"] = False
    out = verify_shadow_reality_lease(r)
    assert out["shadow_collection_ready"] is False
    assert "EXPLICIT_SHADOW_REALITY_AUTHORITY_MISSING" in out["reasons"]


def test_shadow_result_requires_one_use_escrow_and_zero_credit():
    lease = _lease()
    result = {
        "lease_id": lease["lease_id"],
        "execution_count": 1,
        "lease_consumed_after_execution": True,
        "result_content_addressed": True,
        "result_sha256": "c" * 64,
        "result_escrowed": True,
        "result_visible_to_candidate": False,
        "result_visible_to_optimizer": False,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "promotion_performed": False,
    }
    out = verify_shadow_execution_result(lease, result)
    assert out["shadow_result_escrow_valid"] is True
    assert out["score_release_authorized"] is False


def test_shadow_result_rejects_second_execution():
    lease = _lease()
    result = {
        "lease_id": lease["lease_id"],
        "execution_count": 2,
        "lease_consumed_after_execution": True,
        "result_content_addressed": True,
        "result_sha256": "c" * 64,
        "result_escrowed": True,
        "result_visible_to_candidate": False,
        "result_visible_to_optimizer": False,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "promotion_performed": False,
    }
    assert verify_shadow_execution_result(lease, result)["shadow_result_escrow_valid"] is False


def test_overlap_bound_is_never_worse_than_serial():
    out = makespan_bound(120, 80)
    assert out["serial_seconds"] == 200
    assert out["overlapped_seconds"] == 120
    assert out["maximum_structural_seconds_saved"] == 80
    assert out["structural_speedup_upper_bound"] == 200 / 120
