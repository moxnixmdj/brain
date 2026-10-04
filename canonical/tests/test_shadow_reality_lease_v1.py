from canonical.runtime.shadow_reality_lease_v1 import (
    AUTHORITY_SCHEMA,
    classify_shadow_result_after_fixed_point,
    lease_digest,
    verify_shadow_lease,
)
from canonical.runtime.generic_precommit_isolation_theorem_v1 import commitment_digest


def isolation_receipt():
    r = {}
    for i, c in enumerate(("candidate", "harness", "scorer", "environment", "policy"), start=1):
        r[f"{c}_sha256"] = str(i) * 64
        r[f"observed_{c}_sha256"] = str(i) * 64
    r.update({
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
            ["unrelated_zero_reality_work", "unrelated_artifact"],
        ],
    })
    r["commitment_sha256"] = commitment_digest(r)
    return r


def adapter():
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


def activation():
    return {
        "schema": AUTHORITY_SCHEMA,
        "active": True,
        "shadow_collection_authority": True,
        "independent_verification_pass": True,
        "zero_incremental_spend_only": True,
        "write_only_escrow_only": True,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authority": False,
        "promotion_authority": False,
    }


def lease():
    x = {
        "lease_id": "shadow:livebench-if:epoch-1",
        "benchmark_id": "LIVEBENCH_IF_GE_65_7",
        "candidate_sha256": "a" * 64,
        "benchmark_contract_sha256": "b" * 64,
        "population_manifest_sha256": "c" * 64,
        "escrow_sink_contract_sha256": "d" * 64,
        "one_use_nonce": "nonce-001",
        "candidate_frozen": True,
        "candidate_mutation_blocked": True,
        "unrelated_work_mutation_blocked": True,
        "zero_incremental_spend_guard_pass": True,
        "independent_executor": True,
        "one_use_lease": True,
        "lease_consumed": False,
        "escrow_write_only": True,
        "result_read_blocked_until_zero_reality_fixed_point": True,
        "outputs_bound_to_lease": True,
        "result_visible_to_candidate": False,
        "result_visible_to_planner": False,
        "result_visible_to_zero_reality_work": False,
    }
    x["lease_digest_sha256"] = lease_digest(x)
    return x


def test_ready_lease_grants_only_shadow_collection():
    out = verify_shadow_lease(lease(), isolation_receipt(), adapter(), activation())
    assert out["shadow_collection_ready"] is True
    assert out["shadow_collection_authority"] is True
    assert out["global_fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False
    assert out["promotion_authority"] is False
    assert out["execution_authority_beyond_shadow_collection"] is False
    assert out["result_visibility"] == "WRITE_ONLY_ESCROW"


def test_candidate_policy_cannot_self_activate():
    a = activation()
    a["independent_verification_pass"] = False
    out = verify_shadow_lease(lease(), isolation_receipt(), adapter(), a)
    assert out["shadow_collection_ready"] is False
    assert "SHADOW_ACTIVATION_NOT_INDEPENDENTLY_VERIFIED" in out["reasons"]


def test_global_fresh_reality_authority_is_rejected_not_inherited():
    a = activation()
    a["global_fresh_reality_authority"] = True
    out = verify_shadow_lease(lease(), isolation_receipt(), adapter(), a)
    assert out["shadow_collection_ready"] is False
    assert "SHADOW_ACTIVATION_MUST_NOT_GRANT_GLOBAL_FRESH_REALITY" in out["reasons"]


def test_any_result_visibility_breaks_shadow_lease():
    x = lease()
    x["result_visible_to_planner"] = True
    x["lease_digest_sha256"] = lease_digest(x)
    out = verify_shadow_lease(x, isolation_receipt(), adapter(), activation())
    assert out["shadow_collection_ready"] is False
    assert "RESULT_MUST_NOT_BE_VISIBLE_TO_PLANNER" in out["reasons"]


def test_candidate_mutability_breaks_shadow_lease():
    x = lease()
    x["candidate_mutation_blocked"] = False
    x["lease_digest_sha256"] = lease_digest(x)
    out = verify_shadow_lease(x, isolation_receipt(), adapter(), activation())
    assert out["shadow_collection_ready"] is False
    assert "LEASE_GATE_FALSE:candidate_mutation_blocked" in out["reasons"]


def test_thin_adapter_failure_breaks_shadow_lease():
    ad = adapter()
    ad["exact_comparator_identity_verified"] = False
    out = verify_shadow_lease(lease(), isolation_receipt(), ad, activation())
    assert out["shadow_collection_ready"] is False
    assert "BENCHMARK_THIN_ADAPTER_NOT_PROVED" in out["reasons"]


def test_generic_isolation_failure_breaks_shadow_lease():
    iso = isolation_receipt()
    iso["observed_policy_sha256"] = "9" * 64
    out = verify_shadow_lease(lease(), iso, adapter(), activation())
    assert out["shadow_collection_ready"] is False
    assert "GENERIC_PRECOMMIT_ISOLATION_NOT_PROVED" in out["reasons"]


def test_consumed_lease_cannot_replay():
    x = lease()
    x["lease_consumed"] = True
    x["lease_digest_sha256"] = lease_digest(x)
    out = verify_shadow_lease(x, isolation_receipt(), adapter(), activation())
    assert out["shadow_collection_ready"] is False
    assert "LEASE_ALREADY_CONSUMED_OR_STATE_UNKNOWN" in out["reasons"]


def test_post_fixed_point_result_still_never_self_promotes():
    out = classify_shadow_result_after_fixed_point(
        zero_reality_fixed_point_reached=True,
        shadow_lease_passed=True,
        route_still_required=True,
        output_bound_to_lease=True,
        independent_result_verification_pass=True,
    )
    assert out["eligible_for_predicate_specific_reduction"] is True
    assert out["acceptance_credit_authorized"] is False
    assert out["promotion_authority"] is False
    assert out["separate_predicate_specific_activation_required"] is True


def test_dominated_shadow_result_is_deleted_after_fixed_point():
    out = classify_shadow_result_after_fixed_point(
        zero_reality_fixed_point_reached=True,
        shadow_lease_passed=True,
        route_still_required=False,
        output_bound_to_lease=True,
        independent_result_verification_pass=True,
    )
    assert out["eligible_for_predicate_specific_reduction"] is False
    assert out["discard_as_dominated_or_stale"] is True
