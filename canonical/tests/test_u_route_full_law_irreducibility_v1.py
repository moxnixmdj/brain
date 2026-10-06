from canonical.runtime.u_route_full_law_irreducibility_v1 import (
    finite_u_route_theorem,
    partial_information_counterexample,
)


def test_equal_laws_pass_all_indicator_utilities():
    out = finite_u_route_theorem((0.2,0.3,0.5),(0.2,0.3,0.5))
    assert out["indicator_noninferiority_for_all_events"] is True
    assert out["laws_equal"] is True
    assert out["theorem_holds"] is True


def test_distinct_laws_cannot_dominate_for_all_indicator_utilities():
    out = finite_u_route_theorem((0.2,0.3,0.5),(0.2,0.4,0.4))
    assert out["laws_equal"] is False
    assert out["indicator_noninferiority_for_all_events"] is False
    assert out["theorem_holds"] is True


def test_nontrivial_ambiguity_set_cannot_be_robustly_dominated_in_u():
    out = partial_information_counterexample()
    assert out["dominates_target_a_for_all_indicators"] is False
    assert out["dominates_target_b_for_all_indicators"] is False
    assert out["nontrivial_u_robust_dominance_exists"] is False
