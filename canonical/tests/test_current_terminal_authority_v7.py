from canonical.runtime.current_terminal_authority_v7_verifier import verify

def test_v7_semantic_escape_normal_form_passes_exact_sources():
    out=verify()
    assert out["pass"] is True,out
    assert out["status"]=="PASS__V7_SEMANTIC_ESCAPE_NORMAL_FORM__TERMINAL_FALSE__ZERO_CREDIT"
    assert out["open_truth_obligations"]==29
    assert out["accepted_families"]==5
    assert out["open_families"]==14
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0

def test_v7_scheduler_and_frontier_counts():
    out=verify()
    assert out["scheduler_first"]=="C"
    assert out["coarse_escape_role_count"]==6
    assert out["primitive_escape_role_count_after_C"]==5
    assert out["C_remaining_binding_count"]==4
