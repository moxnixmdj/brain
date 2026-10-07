from canonical.runtime import terminal_frontier_factorizer_v7_candidate as f


def test_candidate_counts():
    out = f.factorize()
    assert out["independent_acceptance_conjunct_count"] == 15
    assert out["direct_result_count"] == 15
    assert out["structural_independent_count"] == 0
    assert out["structural_abc_refinement_count"] == 4
    assert out["composition_derived_inside_abc_count"] == 1
    assert out["meta_refinement_count"] == 8
    assert out["route_counts"] == {"D": 15, "U": 0, "J": 0, "G": 0, "T": 0}
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0


def test_exact_structural4_preserved_inside_abc():
    assert set(f.ABC_STRUCTURAL_REFINEMENTS) == f.EXPECTED_STRUCTURAL
    assert set(f.ABC_REFINEMENT_RULES) == f.EXPECTED_STRUCTURAL


def test_no_structural_semantics_deleted():
    out = f.factorize()
    assert set(out["abc_structural_refinements"]) == f.EXPECTED_STRUCTURAL
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in out["derived_inside_abc"]
    assert set(out["terminal_global_surfaces_still_required"]) == {
        "ABC_SELECTED_CONTEXT_COVER",
        "D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE",
    }


def test_direct15_unchanged():
    assert len(f.DIRECT) == 15
    assert len(set(f.DIRECT)) == 15
    assert not (set(f.DIRECT) & f.EXPECTED_STRUCTURAL)
