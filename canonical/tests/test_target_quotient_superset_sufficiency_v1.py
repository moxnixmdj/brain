from canonical.runtime.target_quotient_superset_sufficiency_v1 import (
    SupersetProofError,
    certify_by_superset,
    finite_necessity_countermodel,
)

def test_finite_countermodel_certifies_without_exact_membership_enumeration():
    c = finite_necessity_countermodel()
    assert c.target_subset
    assert c.dominates_target
    assert c.inherited_conditions
    assert c.inherited_resources
    assert c.inherited_ownership

def test_target_outside_superset_fails_closed():
    try:
        certify_by_superset({"a","c"},{"a","b"},{"a":True,"b":True})
    except SupersetProofError as e:
        assert str(e) == "TARGET_NOT_SUBSET_OF_SUPERSET"
    else:
        raise AssertionError("expected fail-closed target subset rejection")

def test_missing_superset_dominance_fails_closed():
    try:
        certify_by_superset({"a"},{"a","b"},{"a":True})
    except SupersetProofError as e:
        assert str(e).startswith("UNBOUND_SUPERSET_DOMINANCE:")
    else:
        raise AssertionError("expected unbound superset dominance rejection")

def test_superset_failure_does_not_fake_target_failure_or_success():
    c = certify_by_superset(
        {"a"},
        {"a","b"},
        {"a":True,"b":False},
        condition_closure={"a":True,"b":True},
        resource_safety_authority={"a":True,"b":True},
        ownership={"a":True,"b":True},
    )
    assert c.dominates_target is True
    # This test preserves the logical distinction: full-S dominance is sufficient,
    # not necessary. A failed extra class cannot be used to reject the terminal goal
    # when it is outside the actual target.
