from canonical.runtime.terminal_frontier_factorizer_v3 import ATOMIC, META, factorize
from canonical.runtime.terminal_coverage_partition_compiler_v3 import compile_partition

DELETED={
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
}

def test_28_truth_basis_exact():
    assert not (DELETED & set(ATOMIC))
    assert len(ATOMIC)==20
    assert len(META)==8
    out=factorize()
    assert out["truth_obligation_count"]==28
    assert out["atomic_count"]==20
    assert out["meta_count"]==8
    assert out["truth_obligations_deleted"]==4

def test_zero_evidence_route_counts_exact():
    out=compile_partition()
    assert out["truth_obligation_count"]==28
    assert out["route_counts"]=={"J":0,"G":0,"T":0,"D":15,"U":13}
    assert out["truth_obligations_deleted"]==4
    assert out["terminal_credit_delta"]==0
    assert out["ownership_credit_delta"]==0

def test_load_bearing_authority_and_scope_semantics_preserved():
    assert "IF_SCOPE_BOUNDARY_NONINFERIOR" in ATOMIC
    assert "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION" in ATOMIC
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in ATOMIC
