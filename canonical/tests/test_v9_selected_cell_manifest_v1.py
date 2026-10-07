from canonical.runtime.v9_selected_cell_manifest_verifier_v1 import verify

def test_manifest_exact_partition():
    x=verify()
    assert x["pass"] is True,x
    assert x["truth_leaf_count"]==29
    assert x["route_bundle_count"]>=1
    assert x["metric_class_count"]>=1
    assert x["terminal_credit_delta"]==0
