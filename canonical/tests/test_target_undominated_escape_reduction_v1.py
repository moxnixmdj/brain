from canonical.runtime.target_undominated_escape_reduction_v1 import (
    certify_undominated_escape_reduction,
    exclusion_certificate_suffices,
    finite_counterexample_to_full_superdomain_dominance_necessity,
)

def test_exact_equivalence_on_finite_sets():
    c=certify_undominated_escape_reduction(
        target={"a","c"},
        superdomain={"a","b","c"},
        brain_dominated={"a","c"},
    )
    assert c.target_dominance_certified is True
    assert c.undominated_escape_region==("b",)
    assert c.target_escape_intersection==()

def test_one_target_escape_kills_certificate():
    c=certify_undominated_escape_reduction(
        target={"a","b"},
        superdomain={"a","b","c"},
        brain_dominated={"a","c"},
    )
    assert c.target_dominance_certified is False
    assert c.target_escape_intersection==("b",)

def test_excluding_only_escape_region_is_enough():
    assert exclusion_certificate_suffices(
        superdomain={"a","b","c"},
        brain_dominated={"a","c"},
        excluded_from_target={"b"},
    )

def test_full_superdomain_dominance_is_not_necessary():
    x=finite_counterexample_to_full_superdomain_dominance_necessity()
    assert x["target_relative_dominance_true"] is True
    assert x["escape_region"]==["b"]
    assert x["escape_exclusion_suffices"] is True
    assert x["exact_target_membership_required"] is False
    assert x["terminal_credit_delta"]==0
