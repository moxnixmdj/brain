from canonical.runtime.terminal_frontier_factorizer_v5 import (
    ATOMIC, META_REFINEMENTS, EXTERNAL_RESULT_ATOMS, META_TO_ABC, factorize
)

def test_20_independent_conjunct_normal_form():
    out=factorize()
    assert len(ATOMIC)==20
    assert len(META_REFINEMENTS)==8
    assert out["independent_truth_count"]==20
    assert out["direct_result_count"]==15
    assert out["structural_independent_count"]==5
    assert out["verified_independent_truth_deletions"]==4
    assert out["absorbed_context_refinements"]==8

def test_if_zero_not_independent():
    assert "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS" not in ATOMIC

def test_meta_burdens_preserved_as_abc_refinements():
    for m in META_REFINEMENTS:
        assert META_TO_ABC[m]==["ABC_SELECTED_CONTEXT_COVER"]

def test_key_scope_truths_preserved():
    for x in (
      "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
      "IF_SCOPE_BOUNDARY_NONINFERIOR",
      "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    ):
        assert x in ATOMIC

def test_no_credit():
    out=factorize()
    assert out["terminal_credit_delta"]==0
    assert out["acceptance_credit_delta"]==0
    assert out["ownership_credit_delta"]==0
