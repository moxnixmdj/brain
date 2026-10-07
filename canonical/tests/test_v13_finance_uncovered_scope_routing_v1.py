from canonical.runtime.v13_finance_uncovered_scope_routing_verifier_v1 import verify,route_sets,FIN,STRUCTURAL_LEGACY

def test_live_source_bound_repair_passes():
    out=verify()
    assert out["pass"] is True,out
    assert out["benchmark_or_target_relative_count"]==14
    assert out["objective_or_structural_count"]==5

def test_finance_moves_out_of_legacy_external_lane():
    atomic,legacy,targetlike,objective=route_sets()
    assert FIN in legacy
    assert FIN not in targetlike
    assert FIN in objective
    assert objective==STRUCTURAL_LEGACY|{FIN}
    assert atomic==targetlike|objective

def test_repair_preserves_all_19_interfaces():
    atomic,legacy,targetlike,objective=route_sets()
    assert len(atomic)==19
    assert len(targetlike)+len(objective)==19
