import copy
from canonical.runtime.unbarred_matched_parity_acceptance_v1 import evaluate

FLAGS = {
    "protocol_schema":"PROJECT_BRAIN_UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1",
    "exact_comparator":"Claude Opus 5.5",
    "family_behavior_frozen":True,
    "brain_package_frozen":True,
    "comparator_surface_frozen":True,
    "challenge_source_pool_frozen":True,
    "selection_after_candidate_freeze":True,
    "same_task_input":True,
    "same_visible_information":True,
    "same_jit_knowledge_sources":True,
    "same_tool_classes":True,
    "same_external_action_authority":True,
    "same_task_time_or_step_budget":True,
    "same_scoring_rubric":True,
    "identity_blinded_to_adjudicators":True,
    "zero_case_replacement":True,
    "zero_adaptive_tuning":True,
    "donor_capability_routes_blocked":True,
    "provenance_complete":True,
    "zero_incremental_spend":True,
    "balanced_scope_rounds":True,
}

def scope(sid,n,brain=1.0,opus=0.0):
    return {
        "scope_id":sid,
        "required":True,
        "scope_definition_frozen":True,
        "scorer_frozen":True,
        "case_scores_independent_conditionally_on_frozen_population":True,
        "paired_cases":[
            {
                "case_id":f"{sid}-{i}",
                "brain_case_id":f"{sid}-{i}",
                "opus_case_id":f"{sid}-{i}",
                "brain_score":brain,
                "opus_score":opus,
            }
            for i in range(n)
        ],
    }

def test_one_scope_exact_first_pass_n19():
    d={**FLAGS,"required_scopes":[scope("whole",19)]}
    out=evaluate(d)
    assert out["pass"] is True, out
    assert out["global_first_all_scope_pass_n"]==19

def test_two_scopes_exact_first_pass_n21():
    d={**FLAGS,"required_scopes":[scope("leaf-a",21),scope("leaf-b",21)]}
    out=evaluate(d)
    assert out["pass"] is True, out
    assert out["global_first_all_scope_pass_n"]==21

def test_post_pass_continuation_fails_closed():
    d={**FLAGS,"required_scopes":[scope("whole",20)]}
    out=evaluate(d)
    assert out["pass"] is False
    assert any(x.startswith("GLOBAL_STOP_RULE_VIOLATED") for x in out["errors"])

def test_brain_below_opus_does_not_pass():
    d={**FLAGS,"required_scopes":[scope("whole",30,brain=0.0,opus=1.0)]}
    out=evaluate(d)
    assert out["status"]=="FAIL_BOUND_NOT_MET"
    assert out["pass"] is False

def test_wrong_comparator_fails_closed():
    d={**FLAGS,"required_scopes":[scope("whole",19)]}
    d["exact_comparator"]="Some Other Model"
    out=evaluate(d)
    assert out["status"]=="FAIL_CLOSED"
    assert "EXACT_COMPARATOR_MISMATCH" in out["errors"]

def test_case_identity_mismatch_fails_closed():
    d={**FLAGS,"required_scopes":[scope("whole",19)]}
    d["required_scopes"][0]["paired_cases"][0]["opus_case_id"]="different"
    out=evaluate(d)
    assert out["status"]=="FAIL_CLOSED"
    assert any(x.startswith("CASE_IDENTITY_MISMATCH") for x in out["errors"])

def test_unbalanced_scope_rounds_fail_closed():
    d={**FLAGS,"required_scopes":[scope("a",21),scope("b",20)]}
    out=evaluate(d)
    assert out["status"]=="FAIL_CLOSED"
    assert "UNBALANCED_SCOPE_ROUND_COUNTS" in out["errors"]

def test_missing_freeze_invariant_fails_closed():
    d={**FLAGS,"required_scopes":[scope("whole",19)]}
    d["brain_package_frozen"]=False
    out=evaluate(d)
    assert out["status"]=="FAIL_CLOSED"
    assert "BRAIN_PACKAGE_FROZEN_NOT_TRUE" in out["errors"]
