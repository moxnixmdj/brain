from canonical.runtime.v14_p2_professional_top_law_selected_cell_verifier_v1 import verify

def test_p2_selected_cell_top_law_candidate():
    out=verify()
    assert out["pass"] is True,out
    assert out["selected_cell_case_count"]==30
    assert out["top_law_selected_cell_candidate"] is True
    assert out["whole_professional_scope_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
