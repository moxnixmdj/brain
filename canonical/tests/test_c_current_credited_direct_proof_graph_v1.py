from canonical.runtime.c_current_credited_direct_proof_graph_v1 import verify_current

def test_current_credited_graph_has_only_direct_roots():
    out=verify_current()
    assert out["pass"] is True,out
    assert out["accepted_family_count"]==5
    assert out["direct_root_count"]==5
    assert out["transport_edge_count"]==0
    assert out["current_C_transport_certificates_required"]==0

def test_future_transport_is_still_fail_closed():
    out=verify_current()
    assert out["future_transport_promotion_requires_local_C_certificate"] is True
    assert out["terminal_credit_delta"]==0
