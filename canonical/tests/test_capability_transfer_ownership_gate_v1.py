from canonical.runtime.capability_transfer_ownership_gate_v1 import evaluate

def valid_transfer():
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

def test_clean_distillation_passes():
    out=evaluate(valid_transfer())
    assert out["pass"] is True

def test_teacher_at_inference_is_forbidden():
    row=valid_transfer()
    row["online_teacher_call_count"]=1
    row["donor_runtime_dependency_count"]=1
    out=evaluate(row)
    assert out["pass"] is False
    assert "ZERO_REQUIRED:online_teacher_call_count" in out["errors"]

def test_teacher_fallback_is_forbidden():
    row=valid_transfer()
    row["teacher_fallback_path_count"]=1
    out=evaluate(row)
    assert out["pass"] is False

def test_local_copied_teacher_is_not_transfer():
    row=valid_transfer()
    row["student_or_derived_artifact_distinct_from_donor"]=False
    row["operative_solver_role"]="EXTERNAL_MODEL_WEIGHTS_REHOSTED_LOCALLY"
    out=evaluate(row)
    assert out["pass"] is False

def test_external_model_replacement_is_still_forbidden():
    row=valid_transfer()
    row["external_model_runtime_dependency_count"]=1
    out=evaluate(row)
    assert out["pass"] is False

def test_distillation_without_post_deletion_qualification_fails():
    row=valid_transfer()
    row["qualification_performed_after_donor_removal"]=False
    out=evaluate(row)
    assert out["pass"] is False

def test_heldout_contamination_fails():
    row=valid_transfer()
    row["heldout_not_used_for_training_selection_or_tuning"]=False
    out=evaluate(row)
    assert out["pass"] is False

def test_unknown_transfer_label_cannot_bypass():
    row=valid_transfer()
    row["transfer_method"]="TOTALLY_NOT_A_MODEL_TRUST_ME"
    out=evaluate(row)
    assert out["pass"] is False
