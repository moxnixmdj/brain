from __future__ import annotations

from canonical.runtime.pre_exposure_isolation_plan_v1 import (
    SCHEMA as PLAN_SCHEMA,
    commitment_digest,
    plan_digest,
    verify_pre_exposure_plan,
)
from canonical.runtime.shadow_reality_lease_v2 import (
    AUTHORITY_SCHEMA,
    CLAIM_SCHEMA,
    claim_digest,
    lease_digest,
    verify_one_use_claim,
    verify_post_execution_result,
    verify_preclaim_readiness,
)
from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    commitment_digest as post_commitment_digest,
)

SHA40 = "a" * 40


def receipt(path: str):
    return {"path": path, "git_blob_sha": SHA40}


def plan():
    x = {"schema": PLAN_SCHEMA}
    for i, c in enumerate(("candidate", "harness", "scorer", "environment", "policy"), start=1):
        x[f"{c}_sha256"] = str(i) * 64
        x[f"pre_reveal_observed_{c}_sha256"] = str(i) * 64
    x.update({
        "commit_event_sequence": 10,
        "pre_reveal_verification_event_sequence": 20,
        "case_reveal_has_occurred": False,
        "execution_has_started": False,
        "evaluation_output_exists": False,
        "independent_executor_bound": True,
        "committed_components_immutable": True,
        "candidate_mutation_blocked": True,
        "unrelated_work_mutation_blocked": True,
        "terminal_case_source_inaccessible_before_claim": True,
        "reveal_step_requires_verified_activation": True,
        "reveal_step_requires_verified_one_use_claim": True,
        "reveal_step_requires_point_of_use_preflight_pass": True,
        "outputs_bound_to_commitment_and_lease": True,
        "write_only_escrow_sink_bound": True,
        "result_read_blocked_until_zero_reality_fixed_point": True,
        "post_execution_isolation_receipt_mandatory": True,
        "fail_closed_on_any_component_drift": True,
        "workflow_control_receipt": receipt("canonical/verification/workflow-control.json"),
        "escrow_contract_receipt": receipt("canonical/verification/escrow-contract.json"),
    })
    x["commitment_sha256"] = commitment_digest(x)
    x["plan_sha256"] = plan_digest(x)
    return x


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
        "two_phase_isolation_protocol_required": True,
        "durable_one_use_claim_backend_verified": True,
        "point_of_use_preflight_required": True,
        "post_execution_isolation_receipt_required": True,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authority": False,
        "promotion_authority": False,
        "independent_verification_receipt": receipt("canonical/verification/activation.json"),
        "claim_backend_verification_receipt": receipt("canonical/verification/claim-backend.json"),
    }


def lease(p):
    x = {
        "lease_id": "shadow:livebench-if:epoch-1",
        "benchmark_id": "LIVEBENCH_IF_GE_65_7",
        "candidate_sha256": "1" * 64,
        "benchmark_contract_sha256": "b" * 64,
        "population_manifest_sha256": "c" * 64,
        "escrow_sink_contract_sha256": "d" * 64,
        "pre_exposure_plan_sha256": p["plan_sha256"],
        "one_use_nonce": "nonce-001",
        "lease_claimed": False,
        "case_reveal_has_occurred": False,
        "result_exists": False,
        "candidate_frozen": True,
        "candidate_mutation_blocked": True,
        "unrelated_work_mutation_blocked": True,
        "zero_incremental_spend_guard_bound": True,
        "independent_executor_bound": True,
        "one_use_lease": True,
        "escrow_write_only": True,
        "result_read_blocked_until_zero_reality_fixed_point": True,
        "outputs_bound_to_lease": True,
        "point_of_use_preflight_required": True,
        "post_execution_isolation_receipt_required": True,
    }
    x["lease_digest_sha256"] = lease_digest(x)
    return x


def claim(l):
    x = {
        "schema": CLAIM_SCHEMA,
        "lease_digest_sha256": l["lease_digest_sha256"],
        "one_use_nonce": l["one_use_nonce"],
        "claim_store_key": "claims/" + l["lease_digest_sha256"],
        "preflight_event_sequence": 30,
        "claim_event_sequence": 31,
        "case_reveal_has_occurred": False,
        "execution_has_started": False,
        "durable_unique_insert_succeeded": True,
        "claim_backend_independently_verified": True,
        "point_of_use_preflight_pass": True,
        "claim_store_previously_absent": True,
        "claim_backend_receipt": receipt("canonical/verification/claim-backend.json"),
    }
    x["claim_digest_sha256"] = claim_digest(x)
    return x


def post_receipt():
    r = {}
    for i, c in enumerate(("candidate", "harness", "scorer", "environment", "policy"), start=1):
        r[f"{c}_sha256"] = str(i) * 64
        r[f"observed_{c}_sha256"] = str(i) * 64
    r.update({
        "commit_event_sequence": 10,
        "case_reveal_event_sequence": 40,
        "execution_start_event_sequence": 41,
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
    r["commitment_sha256"] = post_commitment_digest(r)
    return r


def test_pre_exposure_plan_pass_has_zero_case_reveal_authority():
    out = verify_pre_exposure_plan(plan())
    assert out["pre_exposure_plan_pass"] is True
    assert out["case_reveal_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False


def test_future_event_assertions_are_forbidden_before_exposure():
    p = plan()
    p["case_reveal_event_sequence"] = 21
    p["plan_sha256"] = plan_digest(p)
    out = verify_pre_exposure_plan(p)
    assert out["pre_exposure_plan_pass"] is False
    assert "FUTURE_EVENT_FIELD_FORBIDDEN_PRE_EXPOSURE:case_reveal_event_sequence" in out["reasons"]


def test_plan_mutation_breaks_plan_digest():
    p = plan()
    p["candidate_mutation_blocked"] = False
    out = verify_pre_exposure_plan(p)
    assert out["pre_exposure_plan_pass"] is False
    assert "PLAN_DIGEST_MISMATCH" in out["reasons"]


def test_preclaim_readiness_still_grants_no_case_reveal():
    p = plan()
    l = lease(p)
    out = verify_preclaim_readiness(l, p, adapter(), activation())
    assert out["preclaim_ready"] is True
    assert out["case_reveal_authority"] is False
    assert out["one_use_claim_required"] is True
    assert out["acceptance_credit_authorized"] is False


def test_preclaim_rejects_bad_plan_binding():
    p = plan()
    l = lease(p)
    l["pre_exposure_plan_sha256"] = "9" * 64
    l["lease_digest_sha256"] = lease_digest(l)
    out = verify_preclaim_readiness(l, p, adapter(), activation())
    assert out["preclaim_ready"] is False
    assert "LEASE_PRE_EXPOSURE_PLAN_BINDING_MISMATCH" in out["reasons"]


def test_one_use_claim_is_the_first_stage_that_can_grant_case_reveal():
    p = plan()
    l = lease(p)
    pre = verify_preclaim_readiness(l, p, adapter(), activation())
    out = verify_one_use_claim(claim(l), l, preclaim_ready=pre["preclaim_ready"])
    assert out["one_use_claim_pass"] is True
    assert out["case_reveal_authority"] is True
    assert out["shadow_collection_authority"] is True
    assert out["global_fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False


def test_claim_without_durable_unique_insert_is_blocked():
    p = plan()
    l = lease(p)
    pre = verify_preclaim_readiness(l, p, adapter(), activation())
    c = claim(l)
    c["durable_unique_insert_succeeded"] = False
    c["claim_digest_sha256"] = claim_digest(c)
    out = verify_one_use_claim(c, l, preclaim_ready=pre["preclaim_ready"])
    assert out["one_use_claim_pass"] is False
    assert "DURABLE_UNIQUE_INSERT_NOT_PROVED" in out["reasons"]
    assert out["case_reveal_authority"] is False


def test_claim_after_case_reveal_is_blocked():
    p = plan()
    l = lease(p)
    pre = verify_preclaim_readiness(l, p, adapter(), activation())
    c = claim(l)
    c["case_reveal_has_occurred"] = True
    c["claim_digest_sha256"] = claim_digest(c)
    out = verify_one_use_claim(c, l, preclaim_ready=pre["preclaim_ready"])
    assert out["one_use_claim_pass"] is False
    assert "CLAIM_MUST_PRECEDE_CASE_REVEAL" in out["reasons"]


def test_post_execution_receipt_is_separate_and_still_zero_credit():
    p = plan()
    l = lease(p)
    pre = verify_preclaim_readiness(l, p, adapter(), activation())
    cv = verify_one_use_claim(claim(l), l, preclaim_ready=pre["preclaim_ready"])
    out = verify_post_execution_result(
        claim_verdict=cv,
        post_execution_isolation_receipt=post_receipt(),
        output_bound_to_lease=True,
        result_in_write_only_escrow=True,
    )
    assert out["shadow_result_protocol_valid"] is True
    assert out["eligible_for_future_post_fixed_point_reduction"] is True
    assert out["result_visibility_before_fixed_point"] is False
    assert out["acceptance_credit_authorized"] is False
    assert out["separate_post_fixed_point_predicate_activation_required"] is True


def test_post_execution_feedback_path_invalidates_result():
    p = plan()
    l = lease(p)
    pre = verify_preclaim_readiness(l, p, adapter(), activation())
    cv = verify_one_use_claim(claim(l), l, preclaim_ready=pre["preclaim_ready"])
    r = post_receipt()
    r["observed_causal_edges"].append(["evaluation_output", "candidate"])
    out = verify_post_execution_result(
        claim_verdict=cv,
        post_execution_isolation_receipt=r,
        output_bound_to_lease=True,
        result_in_write_only_escrow=True,
    )
    assert out["shadow_result_protocol_valid"] is False
