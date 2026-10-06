from canonical.runtime.matched_success_zero_reality_cut_v1 import evaluate


def test_current_zero_reality_cut():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["open_zero_reality_premise_count"] == 3
    assert out["brain_first_can_reduce_opus_cases"] is True
    assert out["best_case_opus_case_count"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["fresh_reality_authorized"] is False
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
