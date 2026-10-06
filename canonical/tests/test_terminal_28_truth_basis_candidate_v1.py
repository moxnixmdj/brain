from canonical.runtime.terminal_frontier_factorizer_v3_candidate import (
    ATOMIC, META, EXTERNAL_RESULT_ATOMS, factorize
)

DELETED="IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"

def test_exact_28_truth_basis_candidate():
    assert DELETED not in ATOMIC
    assert len(ATOMIC)==20
    assert len(META)==8
    out=factorize()
    assert out["truth_obligation_count"]==28
    assert out["atomic_count"]==20
    assert out["meta_count"]==8
    assert out["truth_obligations_deleted"]==4
    assert DELETED not in out["obligation_interfaces"]

def test_zero_evidence_route_counts_candidate():
    obligations=set(ATOMIC)|set(META)
    d=set(EXTERNAL_RESULT_ATOMS)
    assert d <= obligations
    assert len(d)==15
    assert len(obligations-d)==13

def test_load_bearing_scope_truths_preserved():
    assert "IF_SCOPE_BOUNDARY_NONINFERIOR" in ATOMIC
    assert "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION" in ATOMIC
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in ATOMIC

def test_no_credit_from_basis_compression():
    assert factorize()["terminal_credit_delta"]==0
