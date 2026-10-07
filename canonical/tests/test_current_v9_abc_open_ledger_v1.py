from canonical.runtime.current_v9_abc_open_ledger_v1 import compile_ledger

def test_current_v9_open_ledger():
    out=compile_ledger()
    assert out["pass"] is True, out
    assert out["unresolved_family_count"]==14
    assert out["owned_structural_generator_count"]==5
    assert out["route_selection_summary"]["fully_content_addressed_selected_routes"]==0
    assert out["route_selection_summary"]["donor_routes_selected"]==0
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
