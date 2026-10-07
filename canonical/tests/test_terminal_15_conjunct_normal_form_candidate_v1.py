from canonical.runtime.terminal_frontier_factorizer_v7_candidate import factorize

def test_15_independent_conjuncts():
    out=factorize()
    assert out["independent_acceptance_conjunct_count"] == 15
    assert out["direct_result_count"] == 15
    assert out["route_counts"] == {"D":15,"U":0,"J":0,"G":0,"T":0}
    assert out["abc_closed"] is False

def test_u4_and_composition_preserved_inside_abc():
    out=factorize()
    derived=set(out["derived_inside_abc"])
    assert {
        "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
        "VISION_DENSE_NONCHART_SCOPE",
        "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
        "IF_SCOPE_BOUNDARY_NONINFERIOR",
        "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    } == derived
    assert out["derived_inside_abc_count"] == 5

def test_no_semantic_credit():
    out=factorize()
    assert out["terminal_credit_delta"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
