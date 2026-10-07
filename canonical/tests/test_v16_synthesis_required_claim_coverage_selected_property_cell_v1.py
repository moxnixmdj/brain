from canonical.runtime.v16_synthesis_required_claim_coverage_selected_property_cell_verifier_v1 import verify

def test_synthesis_required_claim_coverage_top_law():
    x=verify()
    assert x["pass"],x
    assert x["K_c_minus_empty"] is True
    assert x["target_information_required"] is False
    assert x["same_package_donor_deletion_bound"] is True

def test_scope_guards():
    x=verify()
    assert x["synthesis_family_closed"] is False
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
