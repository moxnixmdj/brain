from canonical.runtime.terminal_frontier_factorizer_v8_candidate import factorize

def test_one_global_acceptance_semantic():
    out=factorize()
    assert out["independent_acceptance_semantic_count"] == 1
    assert out["independent_acceptance_semantics"] == ["ABC_SELECTED_CONTEXT_COVER_COMPLETE"]
    assert out["independent_scope_specific_acceptance_conjunct_count"] == 0

def test_direct15_preserved_as_local_routes():
    out=factorize()
    assert out["local_direct_evidence_route_count"] == 15
    assert len(set(out["local_direct_evidence_routes"])) == 15

def test_no_scope_or_credit_deletion():
    out=factorize()
    assert out["abc_closed"] is False
    assert out["terminal_credit_delta"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
