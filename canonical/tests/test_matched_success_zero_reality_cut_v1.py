from canonical.runtime.matched_success_zero_reality_cut_v1 import evaluate


def test_current_zero_reality_cut():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["shared_empirical_wave_count"] == 1
    assert out["superportfolio_cases_generated_now"] is False
    assert out["comparator_currently_admissible"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["fresh_reality_authority"] is False
