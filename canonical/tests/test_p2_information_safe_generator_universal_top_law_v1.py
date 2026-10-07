from canonical.runtime.p2_information_safe_generator_universal_top_law_v1 import verify

def test_p2_generator_universal_top_law_source_bound_identity():
    out = verify()
    assert out["pass"] is True, out
    assert out["coverage_equivalent"] is True
    assert out["boolean_assignments_checked"] == 16
    assert out["unsupported_max_utility"] == -3
    assert out["supported_analytical_min_utility"] == 6
    assert out["difficulty_values_proved"] == [1, 2, 3, 4, 5]
    assert out["global_professional_scope_complete"] is False
    assert out["abc_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
    assert out["incremental_spend_usd"] == 0
