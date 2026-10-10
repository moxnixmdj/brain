from canonical.runtime.escape_active_gap_b_causal_reclassification_verify_v1 import evaluate


def test_current_exact_sources_reclassify_all_active_gap_b_rows_without_credit():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["active_gap_b_count_verified"] == 0
    assert out["effective_gap_a_active_count_verified"] == 12
    assert out["parked_unresolved_count_verified"] == 1
    assert out["reclassified_rows"] == [
        "CHARTOGRAPHY_TOOLS_GE_89",
        "PROWORK_GDPVAL_GE_1846",
    ]
    assert out["parked_rows"] == ["TB_SCIENCE_GE_58_7"]
    assert out["row_credit_delta"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
    assert out["terminal_authority"] is False


def test_reclassification_is_explicitly_not_global_totality():
    out = evaluate()
    assert out["pass"] is True, out
    assert "NO_CC_R3" in out["boundary"]
    assert "NO_GLOBAL_ESCAPE_PROGRESS_TOTALITY" in out["boundary"]
