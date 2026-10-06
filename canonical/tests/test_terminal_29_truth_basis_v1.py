from canonical.runtime.terminal_frontier_factorizer_v2 import ATOMIC, META, factorize
from canonical.runtime.terminal_coverage_partition_compiler_v2 import compile_partition


DELETED = "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"


def test_29_truth_basis_exact():
    assert DELETED not in ATOMIC
    assert len(ATOMIC) == 21
    assert len(META) == 8
    out = factorize()
    assert out["truth_obligation_count"] == 29
    assert out["atomic_count"] == 21
    assert out["meta_count"] == 8
    assert out["truth_obligations_deleted"] == 3
    assert DELETED not in out["obligation_interfaces"]


def test_zero_evidence_route_counts_are_exact():
    out = compile_partition()
    assert out["truth_obligation_count"] == 29
    assert out["route_counts"] == {"J": 0, "G": 0, "T": 0, "D": 15, "U": 14}
    assert out["truth_obligations_deleted"] == 3
    assert out["truth_obligations_closed_by_routing_alone"] == 0
    assert out["terminal_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0


def test_other_composition_terminal_truth_preserved():
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in ATOMIC
    assert "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS" in ATOMIC
    assert "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION" in ATOMIC
