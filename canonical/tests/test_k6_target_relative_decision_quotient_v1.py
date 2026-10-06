from canonical.runtime.k6_target_relative_decision_quotient_v1 import (
    DecisionQuotientError, canonical_safe_quotient, cell_sufficient,
    choose_common_action, partition_sufficient, refinement_needed, verify_finite_theorem
)

def test_same_acceptable_signature_merges():
    x={"x":{"a","b"},"y":{"a","b"}}
    assert canonical_safe_quotient(x)==[["x","y"]]
    assert cell_sufficient(x,["x","y"])

def test_overlap_can_be_coarser_than_identical_signature():
    x={"x":{"a","b"},"y":{"b","c"}}
    assert choose_common_action(x,["x","y"])=="b"

def test_disjoint_sets_require_separator():
    x={"x":{"a"},"y":{"b"}}
    assert refinement_needed(x,["x","y"])
    assert partition_sufficient(x,[["x"],["y"]])

def test_abstention_only_if_jointly_acceptable():
    assert choose_common_action({"x":{"wait","a"},"y":{"wait","b"}},["x","y"])=="wait"
    assert refinement_needed({"x":{"wait","a"},"y":{"b"}},["x","y"])

def test_incomplete_partition_rejected():
    x={"x":{"a"},"y":{"a"}}
    assert not partition_sufficient(x,[["x"]])

def test_no_common_action_fails_closed():
    try:
        choose_common_action({"x":{"a"},"y":{"b"}},["x","y"])
    except DecisionQuotientError:
        pass
    else:
        raise AssertionError("must fail closed")

def test_finite_theorem_bundle():
    out=verify_finite_theorem()
    assert out["faithful_world_model_is_not_generically_necessary"] is True
    assert out["terminal_credit_delta"]==0
