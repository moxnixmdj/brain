from canonical.runtime.terminal_closure_reducer import evaluate_manifest


def test_universal_route_requires_explicit_proof():
    out = evaluate_manifest({})
    assert out["achieved"] is False


def test_universal_scope_cover_route():
    families=[{"id":f"F{i}","closure_state":"OPEN"} for i in range(19)]
    predicates={
        "exact_target_family_count_19": True,
        "every_required_behavior_contracted": True,
        "every_required_behavior_has_admissible_proof": True,
        "donor_dependent_required_behaviors_zero": True,
        "unexplained_required_behaviors_zero": True,
        "unresolved_verifier_mutations_zero": True,
        "unresolved_composition_failures_zero": True,
        "contaminated_evidence_used_for_promotion_zero": True,
        "resource_or_authority_violations_zero": True,
        "all_frozen_opus_acceptance_predicates_pass": False,
        "final_donor_deletion_cleanroom_pass": True,
        "proof_bundle_frozen": True,
    }
    counters={
        "uncontracted_required_behaviors":0,
        "unproved_required_behaviors":0,
        "donor_dependent_required_behaviors":0,
        "unresolved_verifier_mutations":0,
        "unresolved_composition_failures":0,
        "contaminated_promotion_evidence":0,
        "resource_or_authority_violations":0,
    }
    proof={
        "proof_kind":"SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id":"scope://opus55/observable-trace",
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "observable_trace_scope_complete":True,
        "all_useful_target_behaviors_in_scope":True,
        "every_admission_sound":True,
        "residual_complement_unsat":True,
        "selected_cover_complete":True,
        "u_empty":True,
        "abc_closed":True,
        "all_credited_routes_brain_owned":True,
        "donor_independence_closed":True,
        "clean_room_replay_pass":True,
        "proof_artifact":{"path":"p","git_blob_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
        "verifier_receipt_artifact":{"path":"v","git_blob_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
    }
    out=evaluate_manifest({
        "expected_family_count":19,
        "actual_family_count":19,
        "families":families,
        "counters":counters,
        "terminal_predicates":predicates,
        "universal_cover_proof":proof,
    })
    assert out["achieved"] is True
    assert out["proof_route"] == "UNIVERSAL_SCOPE_COMPLETE_COVER"
