from canonical.runtime.zero_task_specific_advice_policy_synthesis_v1 import (
    synthesize_finite, finite_theorem, finite_counterexample_resource_bound
)

def test_finite_search_finds_certified_policy_without_task_specific_advice():
    policies=("p0","p1","p2","p3")
    good={"p3"}
    assert finite_theorem(policies, lambda p:p in good, "p3")=="p3"

def test_no_positive_policy_fails_closed():
    try:
        synthesize_finite(("p0","p1"), lambda p:False)
    except LookupError as e:
        assert str(e)=="NO_CERTIFIED_ADEQUATE_POLICY"
    else:
        raise AssertionError("expected fail closed")

def test_empty_policy_universe_fails_closed():
    try:
        synthesize_finite((), lambda p:True)
    except ValueError as e:
        assert str(e)=="EMPTY_POLICY_UNIVERSE"
    else:
        raise AssertionError("expected fail closed")

def test_resource_bound_can_make_generic_search_inadmissible():
    out=finite_counterexample_resource_bound(
        ("p0","p1","p2","p3"),
        lambda p:p=="p3",
        "p3",
        max_checks=2,
    )
    assert out["status"]=="RESOURCE_BOUND_BLOCKS_GENERIC_SEARCH"

def test_resource_bound_not_blocking_when_witness_early():
    out=finite_counterexample_resource_bound(
        ("p0","p1","p2"),
        lambda p:p=="p1",
        "p1",
        max_checks=2,
    )
    assert out["status"]=="FOUND"
    assert out["policy"]=="p1"
