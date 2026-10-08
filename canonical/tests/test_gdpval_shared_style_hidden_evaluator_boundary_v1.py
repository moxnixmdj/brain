from fractions import Fraction

from canonical.runtime.gdpval_shared_style_hidden_evaluator_boundary_v1 import (
    CRITERION,
    analyze,
    deterministic_distribution,
)


def test_distinct_deterministic_artifacts_are_not_universally_ordered():
    out=analyze({
        "criterion":CRITERION,
        "target_distribution":deterministic_distribution("TARGET_ARTIFACT"),
        "brain_distribution":deterministic_distribution("BRAIN_ARTIFACT"),
    })
    assert out["unrestricted_hidden_utility_noninferiority"] is False
    assert out["distinguishing_hidden_utility_indicator_outcome"]=="TARGET_ARTIFACT"


def test_identical_deterministic_artifact_is_universally_tied():
    d=deterministic_distribution("SAME")
    out=analyze({"criterion":CRITERION,"target_distribution":d,"brain_distribution":d})
    assert out["unrestricted_hidden_utility_noninferiority"] is True
    assert out["distinguishing_hidden_utility_indicator_outcome"] is None


def test_different_distributions_fail_unrestricted_universal_order():
    out=analyze({
        "criterion":CRITERION,
        "target_distribution":{"A":Fraction(3,4),"B":Fraction(1,4)},
        "brain_distribution":{"A":Fraction(1,2),"B":Fraction(1,2)},
    })
    assert out["unrestricted_hidden_utility_noninferiority"] is False


def test_no_authority_escalation():
    d=deterministic_distribution("SAME")
    out=analyze({"criterion":CRITERION,"target_distribution":d,"brain_distribution":d})
    assert out["semantic_restriction_proved_by_this_runtime"] is False
    assert out["owner_style_relation_reproduced"] is False
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"]==0
