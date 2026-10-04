from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    commitment_digest,verify_generic_isolation,verify_benchmark_thin_adapter,
    concurrency_admissibility
)

def base_receipt():
    r={}
    for i,c in enumerate(("candidate","harness","scorer","environment","policy"),start=1):
        r[f"{c}_sha256"]=str(i)*64
        r[f"observed_{c}_sha256"]=str(i)*64
    r.update({
      "commit_event_sequence":10,
      "case_reveal_event_sequence":11,
      "execution_start_event_sequence":12,
      "independent_executor":True,
      "committed_components_immutable":True,
      "no_case_or_evaluation_feedback_to_committed_components":True,
      "unrelated_work_cannot_mutate_committed_components":True,
      "outputs_bound_to_commitment":True,
      "observed_causal_edges":[
        ["case_content","execution_output"],
        ["evaluation_output","receipt_store"],
        ["unrelated_zero_reality_work","unrelated_artifact"],
      ],
    })
    r["commitment_sha256"]=commitment_digest(r)
    return r

def base_adapter():
    return {
      "population_identity_verified":True,
      "scorer_or_grader_equivalence_verified":True,
      "effort_and_context_semantics_verified":True,
      "tool_and_environment_boundary_verified":True,
      "exact_comparator_identity_verified":True,
      "no_proxy_substitution_verified":True,
      "zero_incremental_spend_or_entitlement_verified":True,
      "acceptance_rule_bound":True,
    }

def test_generic_theorem_pass_does_not_authorize_reality():
    out=verify_generic_isolation(base_receipt())
    assert out["generic_isolation_kernel_pass"] is True
    assert out["conditional_adaptation_independence_proved"] is True
    assert out["benchmark_comparability_proved"] is False
    assert out["fresh_reality_authority"] is False

def test_precommit_order_is_strict():
    r=base_receipt(); r["case_reveal_event_sequence"]=10
    out=verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False
    assert "PRECOMMIT_ORDER_NOT_PROVED" in out["reasons"]

def test_any_committed_component_drift_rejected():
    r=base_receipt(); r["observed_harness_sha256"]="9"*64
    out=verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False
    assert "EXECUTED_HARNESS_DIFFERS_FROM_COMMITTED" in out["reasons"]

def test_forbidden_feedback_path_rejected_even_if_boolean_claims_true():
    r=base_receipt()
    r["observed_causal_edges"].append(["evaluation_output","candidate"])
    out=verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False
    assert "FORBIDDEN_CAUSAL_PATH:evaluation_output->candidate" in out["reasons"]

def test_indirect_unrelated_mutation_path_rejected():
    r=base_receipt()
    r["observed_causal_edges"].extend([
      ["unrelated_zero_reality_work","shared_state"],
      ["shared_state","policy"],
    ])
    out=verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False
    assert "FORBIDDEN_CAUSAL_PATH:unrelated_zero_reality_work->policy" in out["reasons"]

def test_thin_adapter_is_separate():
    ad=base_adapter()
    out=verify_benchmark_thin_adapter(ad)
    assert out["benchmark_thin_adapter_pass"] is True
    assert out["generic_isolation_kernel_proved"] is False
    bad=dict(ad); bad["effort_and_context_semantics_verified"]=False
    assert verify_benchmark_thin_adapter(bad)["benchmark_thin_adapter_pass"] is False

def test_all_three_gates_required_for_concurrency():
    r=base_receipt(); ad=base_adapter()
    assert concurrency_admissibility(r,ad,explicit_fresh_reality_authority=False)["concurrent_collection_ready"] is False
    assert concurrency_admissibility(r,ad,explicit_fresh_reality_authority=True)["concurrent_collection_ready"] is True
    bad=dict(ad); bad["exact_comparator_identity_verified"]=False
    assert concurrency_admissibility(r,bad,explicit_fresh_reality_authority=True)["concurrent_collection_ready"] is False
