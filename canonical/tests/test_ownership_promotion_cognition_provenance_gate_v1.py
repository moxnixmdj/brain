from canonical.runtime.ownership_promotion_cognition_provenance_gate_v1 import evaluate

def clean_transfer():
    return {
        "transfer_method": "DISTILLATION",
        "acquisition_and_deployment_phases_separated": True,
        "donor_use_confined_to_acquisition": True,
        "brain_owned_operative_artifact": True,
        "operative_artifact_content_addressed": True,
        "applicable_rights_and_provenance_closed": True,
        "donor_access_disabled_during_qualification": True,
        "donor_deletion_behavior_preserved": True,
        "independent_heldout_qualification_pass": True,
        "heldout_not_used_for_training_selection_or_tuning": True,
        "causal_ablation_pass": True,
        "causal_rescue_pass": True,
        "full_runtime_dependency_inventory_complete": True,
        "no_answer_leakage": True,
        "future_use_requires_no_donor_rediscovery": True,
        "donor_runtime_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "undeclared_runtime_dependency_count": 0,
        "qualification_performed_after_donor_removal": True,
        "donor_role": "ACQUISITION_SOURCE_ONLY",
        "operative_solver_role": "BRAIN_OWNED_DERIVED_MECHANISM",
        "student_or_derived_artifact_distinct_from_donor": True,
    }

def test_missing_class_fails_closed():
    assert evaluate({})["pass"] is False

def test_k3_always_fails():
    assert evaluate({"external_contribution_classification":"K3_RUNTIME_COGNITION"})["pass"] is False

def test_k2_requires_transfer_record():
    assert evaluate({"external_contribution_classification":"K2_TRANSFER_DERIVED"})["pass"] is False

def test_clean_k2_passes_gate_but_grants_no_credit():
    out=evaluate({"external_contribution_classification":"K2_TRANSFER_DERIVED","capability_transfer_record":clean_transfer()})
    assert out["pass"] is True
    assert out["promotion_authority"] is False
    assert out["ownership_credit_delta"] == 0

def test_k1_requires_non_authoritative_information_only():
    assert evaluate({
        "external_contribution_classification":"K1_INFORMATION_ONLY",
        "external_knowledge_non_authoritative":True,
        "external_knowledge_target_solving_policy_or_answer":False,
    })["pass"] is True

def test_k1_answer_provider_fails():
    assert evaluate({
        "external_contribution_classification":"K1_INFORMATION_ONLY",
        "external_knowledge_non_authoritative":True,
        "external_knowledge_target_solving_policy_or_answer":True,
    })["pass"] is False

def test_none_rejects_hidden_donor_use():
    assert evaluate({
        "external_contribution_classification":"NONE",
        "acquisition_donor_provenance":{"used":True},
    })["pass"] is False

def test_none_clean_passes():
    assert evaluate({"external_contribution_classification":"NONE"})["pass"] is True
