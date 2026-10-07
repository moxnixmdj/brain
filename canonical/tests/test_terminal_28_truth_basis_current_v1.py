from canonical.runtime.terminal_frontier_factorizer_v4 import (
    ATOMIC, META, EXTERNAL_RESULT_ATOMS, factorize
)

DELETED="IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"

def test_current_28_truth_basis():
    assert DELETED not in ATOMIC
    assert len(ATOMIC)==20
    assert len(META)==8
    out=factorize()
    assert out["truth_obligation_count"]==28
    assert out["truth_obligations_deleted"]==4
    assert out["direct_result_count"]==15
    assert out["unresolved_structural_count"]==13
    assert DELETED not in out["obligation_interfaces"]

def test_scope_and_composition_truths_preserved():
    for x in (
      "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
      "IF_SCOPE_BOUNDARY_NONINFERIOR",
      "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    ):
        assert x in ATOMIC

def test_no_credit_from_deletion():
    out=factorize()
    assert out["terminal_credit_delta"]==0
    assert out["acceptance_credit_delta"]==0
    assert out["ownership_credit_delta"]==0
