from canonical.runtime import terminal_frontier_factorizer_v6_candidate as f

def test_counts():
    out=f.factorize()
    assert out["independent_truth_count"]==19
    assert out["direct_result_count"]==15
    assert out["structural_independent_count"]==4
    assert out["derived_inside_abc_count"]==1
    assert out["meta_refinement_count"]==8
    assert out["route_counts"]=={"D":15,"U":4,"J":0,"G":0,"T":0}

def test_composition_not_independent_but_preserved_derived():
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" not in f.ATOMIC
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in f.DERIVED_INSIDE_ABC
    assert "B9_DERIVATIVE_THEOREM" in f.DERIVED_RULES["COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"]

def test_structural_exact():
    assert f.STRUCTURAL_ATOMS==f.EXPECTED_STRUCTURAL

def test_meta_preserved():
    assert len(f.META_REFINEMENTS)==8
    assert all(f.META_TO_ABC[m]==["ABC_SELECTED_CONTEXT_COVER"] for m in f.META_REFINEMENTS)
