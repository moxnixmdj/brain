from canonical.runtime.two_surface_terminal_normal_form_audit_v1 import audit

def test_two_surface_mapping_is_total_and_exact():
    out=audit()
    assert out["pass"] is True,out
    assert out["burden_cell_count"]==20
    assert out["meta_refinement_count"]==8
    assert out["top_level_surface_count"]==2
    assert out["terminal_credit_delta"]==0
