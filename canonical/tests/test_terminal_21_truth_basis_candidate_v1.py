from canonical.runtime.terminal_frontier_factorizer_v4 import ATOMIC, META, factorize

OLD_META={
"CYBERSECURITY","BIOLOGY_RESEARCH_AND_DEVELOPMENT","AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
"HEALTHCARE","MATHEMATICAL_REASONING_ARXIVMATH","MULTILINGUAL_PERFORMANCE","LONG_CONTEXT",
"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"}

def test_21_truth_basis_candidate():
    out=factorize()
    assert len(ATOMIC)==20
    assert META==("TARGET_COMPLETE_TERMINAL_COVERAGE_CERTIFICATE",)
    assert out["truth_obligation_count"]==21
    assert out["atomic_count"]==20
    assert out["meta_count"]==1
    assert not (OLD_META & set(META))

def test_zero_evidence_route_shape():
    out=factorize()
    assert out["D_count"]==15
    assert out["U_count"]==6

def test_single_meta_is_global_completeness_not_domain_label():
    out=factorize()
    assert out["obligation_interfaces"]["TARGET_COMPLETE_TERMINAL_COVERAGE_CERTIFICATE"]==["TARGET_COMPLETENESS_AND_GLOBAL_COVERAGE"]
    assert out["terminal_credit_delta"]==0
