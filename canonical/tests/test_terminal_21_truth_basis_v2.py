from canonical.runtime.terminal_frontier_factorizer_v4 import ATOMIC, META, factorize
from canonical.runtime.terminal_coverage_partition_compiler_v4 import compile_partition

OLD_META={
"CYBERSECURITY","BIOLOGY_RESEARCH_AND_DEVELOPMENT","AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
"HEALTHCARE","MATHEMATICAL_REASONING_ARXIVMATH","MULTILINGUAL_PERFORMANCE","LONG_CONTEXT",
"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"}

def test_exact_21_truth_basis():
    assert len(ATOMIC)==20
    assert META==("TARGET_COMPLETE_TERMINAL_COVERAGE_CERTIFICATE",)
    assert not (OLD_META & set(META))
    out=factorize()
    assert out["truth_obligation_count"]==21
    assert out["atomic_count"]==20
    assert out["meta_count"]==1

def test_zero_evidence_routes_are_d15_u6():
    out=compile_partition()
    assert out["truth_obligation_count"]==21
    assert out["route_counts"]=={"J":0,"G":0,"T":0,"D":15,"U":6}
    assert out["terminal_credit_delta"]==0
    assert out["ownership_credit_delta"]==0

def test_global_meta_is_fail_closed_unresolved():
    out=compile_partition()
    row=out["classifications"]["TARGET_COMPLETE_TERMINAL_COVERAGE_CERTIFICATE"]
    assert row["route"]=="U"
    assert row["status"]=="UNRESOLVED_FAIL_CLOSED"

def test_underlying_scope_truths_remain_atomic():
    for x in ("IF_SCOPE_BOUNDARY_NONINFERIOR","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"):
        assert x in ATOMIC
