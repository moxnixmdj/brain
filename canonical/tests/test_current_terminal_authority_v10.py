from canonical.runtime.current_terminal_authority_v10_verifier import verify
from canonical.runtime.terminal_frontier_factorizer_v4 import factorize, ATOMIC

def test_v10_exact_28_truth_authority():
    out=verify()
    assert out["pass"] is True,out
    assert out["terminal_credit_delta"]==0

def test_factorizer_counts_match_v10():
    out=factorize()
    assert out["truth_obligation_count"]==28
    assert out["direct_result_count"]==15
    assert out["unresolved_structural_count"]==13
    assert "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS" not in ATOMIC
