from canonical.runtime.unknown_domain_v2_token_collision_bound_v1 import bound

def test_exact_critical_pair_count_and_56_bit_bound():
    out=bound()
    assert out["token_bits"]==56
    assert out["critical_pair_count"]==31
    assert out["prf_union_bound_numerator"]==31
    assert out["prf_union_bound_denominator"]==2**56
    assert out["prf_union_bound_float"] < 4.31e-16
    assert out["unconditional_for_every_secret_theorem_authorized"] is False
    assert out["acceptance_credit"] is False
