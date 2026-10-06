from canonical.runtime.terminal_minimum_information_cut_v4 import compile_cut

def test_exact_current_28_truth_partition():
    out=compile_cut()
    assert out["pass"] is True,out
    assert out["truth_count"]==28
    assert out["counts"]=={
        "FIXED_THRESHOLD_DECISION":13,
        "DIRECT_HIDDEN_ORACLE":1,
        "BRAIN_FIRST_BINARY_MATCHED":3,
        "RELATIVE_SCOPE_OR_QUALITY":3,
        "META_TRANSFER":8,
    }

def test_no_class_claims_terminal_credit_or_execution_authority():
    out=compile_cut()
    assert out["terminal_credit_delta"]==0
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["promotion_authority"] is False

def test_binary_matched_best_case_requires_zero_opus_execution():
    out=compile_cut()
    assert out["opus_execution_best_case"]["BRAIN_FIRST_BINARY_MATCHED"]==0
    assert "ONLY_BRAIN_FAILURE_RESIDUAL" in out["semantic_external_verdict_requirements"]["BRAIN_FIRST_BINARY_MATCHED"]

def test_fixed_threshold_class_requires_bound_verdict_not_exact_score():
    out=compile_cut()
    s=out["semantic_external_verdict_requirements"]["FIXED_THRESHOLD_DECISION"]
    assert "PASS_FAIL_VERDICT" in s
