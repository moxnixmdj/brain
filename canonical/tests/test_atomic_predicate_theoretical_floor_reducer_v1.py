from __future__ import annotations

from canonical.runtime.atomic_predicate_theoretical_floor_reducer_v1 import evaluate


def witness(**updates):
    value = {
        "predicate_id": "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "binds_frozen_predicate": True,
        "closes_entire_predicate": True,
        "metric_nonnegative_proved": True,
        "scope_relation": "EXACT",
        "direction": "lower",
        "brain_upper_bound": 0,
        "theoretical_lower_bound": 0,
        "scope_completeness": {
            "verified": True,
            "independent": True,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "all_admissible_target_inputs_proved": True,
            "formal_completeness": True,
            "receipt": "canonical/verification/example_scope_receipt.json",
        },
    }
    value.update(updates)
    return value


def test_scope_complete_zero_bad_event_floor_removes_comparator():
    out = evaluate(witness())
    assert out["predicate_proved"] is True
    assert out["target_comparator_required_for_this_predicate"] is False
    assert out["status"] == "PASS__THEORETICAL_FLOOR_DOMINANCE"


def test_finite_zero_sample_without_scope_completeness_fails_closed():
    value = witness()
    value.pop("scope_completeness")
    out = evaluate(value)
    assert out["predicate_proved"] is False
    assert "SCOPE_COMPLETENESS_MISSING" in out["failures"]


def test_unverified_scope_fails_closed():
    value = witness()
    value["scope_completeness"] = dict(value["scope_completeness"])
    value["scope_completeness"]["verified"] = False
    out = evaluate(value)
    assert out["predicate_proved"] is False
    assert "SCOPE_COMPLETENESS_NOT_VERIFIED" in out["failures"]


def test_nonzero_brain_bad_event_bound_fails_closed():
    out = evaluate(witness(brain_upper_bound=0.001))
    assert out["predicate_proved"] is False
    assert "BRAIN_UPPER_BOUND_NOT_ZERO" in out["failures"]


def test_nonnegativity_must_be_proved():
    out = evaluate(witness(metric_nonnegative_proved=False))
    assert out["predicate_proved"] is False
    assert "NONNEGATIVITY_NOT_PROVED" in out["failures"]


def test_partial_scope_cannot_close():
    out = evaluate(witness(scope_relation="PARTIAL"))
    assert out["predicate_proved"] is False
    assert "SCOPE_NOT_EXACT_OR_PROVEN_STRONGER" in out["failures"]


def test_exhaustive_finite_superset_is_admissible_only_with_subset_proof():
    value = witness()
    value["scope_completeness"] = {
        "verified": True,
        "independent": True,
        "basis": "EXHAUSTIVE_FINITE_SUPERSET",
        "exhaustive": True,
        "target_subset_proved": True,
        "receipt": "canonical/verification/exhaustive_scope_receipt.json",
    }
    assert evaluate(value)["predicate_proved"] is True

    value["scope_completeness"]["target_subset_proved"] = False
    out = evaluate(value)
    assert out["predicate_proved"] is False
    assert "SCOPE_COMPLETENESS_BASIS_INCOMPLETE" in out["failures"]


def test_target_upper_bound_is_not_needed_at_mathematical_floor():
    value = witness()
    value["target_upper_bound"] = None
    out = evaluate(value)
    assert out["predicate_proved"] is True
    assert out["proof_mode"] == "ABSOLUTE_DOMINANCE_THEORETICAL_FLOOR"
