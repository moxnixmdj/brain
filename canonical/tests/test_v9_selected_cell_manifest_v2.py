from canonical.runtime.v9_selected_cell_manifest_v2_verifier import verify

def test_v9_manifest_v2():
    x=verify()
    assert x["pass"] is True,x
    assert x["atomic_leaf_count"]==21
    assert x["route_bundle_count"]==13
    assert x["meta_refinement_count"]==8
    assert x["current_authority_rows"]==29
    assert x["terminal_credit_delta"]==0
