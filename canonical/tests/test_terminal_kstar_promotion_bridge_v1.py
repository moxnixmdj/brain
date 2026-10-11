from canonical.runtime import terminal_kstar_promotion_bridge_v1 as k

def test_kstar_bridge_preserves_terminal_semantics():
    assert k.ALLOWED == {"FULL_SCOPE_DB_COVER","TARGET_ESCAPE_NONOCCUPANCY","GENERATOR_CLOSURE_SCOPE_COMPLETE","SELECTED_COVER_COMPLEMENT_UNSAT"}
    assert "u_empty" in k.SEM
    assert "all_credited_routes_brain_owned" in k.SEM
    assert "all_frozen_opus_acceptance_predicates_pass" not in k.COMMON
    assert "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json" in k.REQ
    assert "canonical/runtime/terminal_closure_reducer.py" in k.REQ
    assert k.GLOBAL_OWNERSHIP_REDUCER in k.REQ
    assert "zero_external_model_runtime_cognition_dependencies" in k.GLOBAL_OWNERSHIP_REQUIRED_PREDICATES
    assert "donor_deletion_protocol_v2_bound" in k.GLOBAL_OWNERSHIP_REQUIRED_PREDICATES
