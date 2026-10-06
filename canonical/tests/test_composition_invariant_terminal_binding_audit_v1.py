from canonical.runtime.composition_invariant_terminal_binding_audit_v1 import audit_current_authority, verify

def test_current_binding_audit():
    out = audit_current_authority()
    assert out["complete_terminal_noncompensability_mapping_present"] is False
    assert out["conditional_countermodel_trigger_satisfied"] is True
    assert out["automatic_terminal_credit"] is False

def test_verify():
    assert verify().startswith("PASS__")
