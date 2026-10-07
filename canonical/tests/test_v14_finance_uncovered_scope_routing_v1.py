from canonical.runtime.v14_finance_uncovered_scope_routing_verifier_v1 import verify,route_sets,FIN,LEGACY_STRUCTURAL

def test_live_v14_repair_passes():
    x=verify()
    assert x["pass"] is True,x
    assert x["benchmark_or_target_relative_count"]==14
    assert x["objective_or_structural_count"]==5

def test_finance_direct_scope_is_not_target_result_lane():
    atomic,external,targetlike,objective=route_sets()
    assert FIN in external
    assert FIN not in targetlike
    assert FIN in objective
    assert objective==LEGACY_STRUCTURAL|{FIN}

def test_all_legacy_19_interfaces_preserved():
    atomic,external,targetlike,objective=route_sets()
    assert len(atomic)==19
    assert atomic==targetlike|objective
