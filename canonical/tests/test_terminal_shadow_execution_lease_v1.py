from canonical.runtime.terminal_shadow_execution_lease_v1 import evaluate_shadow_lease
from canonical.runtime.generic_precommit_isolation_theorem_v1 import commitment_digest

COMPONENTS=("candidate","harness","scorer","environment","policy")

def isolation_receipt():
    r={}
    for i,c in enumerate(COMPONENTS,start=1):
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
      ],
    })
    r["commitment_sha256"]=commitment_digest(r)
    return r

def adapter():
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

def base():
    return dict(
      isolation_receipt=isolation_receipt(),
      thin_adapter=adapter(),
      benchmark_id="TB_SCIENCE_GE_58_7",
      candidate_epoch="candidate-sha256:abc",
      zero_spend_guard_pass=True,
      result_escrowed=True,
      candidate_can_read_escrow=False,
      planner_can_read_escrow=False,
      benchmark_specific_shadow_authority=True,
    )

def test_shadow_collection_pass_is_not_acceptance():
    out=evaluate_shadow_lease(**base())
    assert out["shadow_collection_ready"] is True
    assert out["result_release_ready"] is False
    assert out["acceptance_credit_authorized"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority_granted_by_this_module"] is False

def test_candidate_result_visibility_rejected():
    x=base(); x["candidate_can_read_escrow"]=True
    out=evaluate_shadow_lease(**x)
    assert out["shadow_collection_ready"] is False
    assert "CANDIDATE_ESCROW_READ_PATH_NOT_EXCLUDED" in out["reasons"]

def test_planner_result_visibility_rejected():
    x=base(); x["planner_can_read_escrow"]=True
    out=evaluate_shadow_lease(**x)
    assert out["shadow_collection_ready"] is False
    assert "PLANNER_ESCROW_READ_PATH_NOT_EXCLUDED" in out["reasons"]

def test_shadow_authority_is_separate_gate():
    x=base(); x["benchmark_specific_shadow_authority"]=False
    out=evaluate_shadow_lease(**x)
    assert out["shadow_collection_ready"] is False
    assert "BENCHMARK_SPECIFIC_SHADOW_AUTHORITY_ABSENT" in out["reasons"]

def test_bad_adapter_rejected():
    x=base(); x["thin_adapter"]=dict(adapter(), exact_comparator_identity_verified=False)
    out=evaluate_shadow_lease(**x)
    assert out["shadow_collection_ready"] is False
    assert "BENCHMARK_THIN_ADAPTER_NOT_PROVED" in out["reasons"]
