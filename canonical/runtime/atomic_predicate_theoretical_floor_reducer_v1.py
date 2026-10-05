"""Fail-closed theoretical-floor reducer for atomic acceptance predicates.

This reducer does not grant acceptance by itself. It decides whether a supplied
atomic-predicate witness is strong enough to remove target-comparator dependence
because the Brain has proved the mathematical optimum of a lower-is-better,
nonnegative bad-event metric over the entire frozen predicate scope.

A finite perfect sample is insufficient. Scope completeness must be independently
verified as exact, exhaustive finite, or universal formal coverage.
"""
from __future__ import annotations

from typing import Any, Mapping

ALLOWED_SCOPE_BASES = {
    "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
    "EXHAUSTIVE_FINITE_SUPERSET",
    "UNIVERSAL_FORMAL_SCOPE_PROOF",
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _scope_complete(scope: Any) -> tuple[bool, str]:
    if not isinstance(scope, Mapping):
        return False, "SCOPE_COMPLETENESS_MISSING"
    if scope.get("verified") is not True:
        return False, "SCOPE_COMPLETENESS_NOT_VERIFIED"
    if scope.get("independent") is not True:
        return False, "SCOPE_COMPLETENESS_NOT_INDEPENDENT"

    basis = scope.get("basis")
    if basis not in ALLOWED_SCOPE_BASES:
        return False, "SCOPE_COMPLETENESS_BASIS_INVALID"

    exact = (
        basis == "EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
        and scope.get("complete_target_case_set") is True
    )
    exhaustive = (
        basis == "EXHAUSTIVE_FINITE_SUPERSET"
        and scope.get("exhaustive") is True
        and scope.get("target_subset_proved") is True
    )
    universal = (
        basis == "UNIVERSAL_FORMAL_SCOPE_PROOF"
        and scope.get("all_admissible_target_inputs_proved") is True
        and scope.get("formal_completeness") is True
    )
    if not (exact or exhaustive or universal):
        return False, "SCOPE_COMPLETENESS_BASIS_INCOMPLETE"

    receipt = scope.get("receipt")
    if not isinstance(receipt, str) or not receipt:
        return False, "SCOPE_COMPLETENESS_RECEIPT_MISSING"
    return True, str(basis)


def evaluate(witness: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a candidate zero-bad-event atomic-predicate witness."""
    failures: list[str] = []

    predicate_id = witness.get("predicate_id")
    if not isinstance(predicate_id, str) or not predicate_id:
        failures.append("PREDICATE_ID_MISSING")

    for key, code in (
        ("verified", "WITNESS_NOT_VERIFIED"),
        ("independent", "WITNESS_NOT_INDEPENDENT"),
        ("contamination_clean", "CONTAMINATION_NOT_CLEAN"),
        ("binds_frozen_predicate", "FROZEN_PREDICATE_NOT_BOUND"),
        ("closes_entire_predicate", "DOES_NOT_CLOSE_ENTIRE_PREDICATE"),
        ("metric_nonnegative_proved", "NONNEGATIVITY_NOT_PROVED"),
    ):
        if witness.get(key) is not True:
            failures.append(code)

    if witness.get("scope_relation") not in {"EXACT", "PROVEN_STRONGER"}:
        failures.append("SCOPE_NOT_EXACT_OR_PROVEN_STRONGER")

    if witness.get("direction") != "lower":
        failures.append("DIRECTION_NOT_LOWER_IS_BETTER")

    brain_upper = _number(witness.get("brain_upper_bound"))
    theoretical_lower = _number(witness.get("theoretical_lower_bound"))
    if brain_upper is None:
        failures.append("BRAIN_UPPER_BOUND_MISSING")
    if theoretical_lower is None:
        failures.append("THEORETICAL_LOWER_BOUND_MISSING")

    # This reducer is intentionally narrow: bad-event counts/rates are
    # nonnegative and their exact mathematical floor is zero.
    if theoretical_lower is not None and theoretical_lower != 0.0:
        failures.append("THEORETICAL_LOWER_BOUND_NOT_ZERO")
    if brain_upper is not None and brain_upper != 0.0:
        failures.append("BRAIN_UPPER_BOUND_NOT_ZERO")

    scope_ok, scope_reason = _scope_complete(witness.get("scope_completeness"))
    if not scope_ok:
        failures.append(scope_reason)

    proved = not failures
    return {
        "schema": "PROJECT_BRAIN_ATOMIC_PREDICATE_THEORETICAL_FLOOR_VERDICT_V1",
        "predicate_id": predicate_id,
        "status": (
            "PASS__THEORETICAL_FLOOR_DOMINANCE"
            if proved
            else "FAIL_CLOSED__THEORETICAL_FLOOR_NOT_PROVED"
        ),
        "predicate_proved": proved,
        "target_comparator_required_for_this_predicate": False if proved else None,
        "proof_mode": "ABSOLUTE_DOMINANCE_THEORETICAL_FLOOR" if proved else None,
        "scope_basis": scope_reason if scope_ok else None,
        "failures": sorted(set(failures)),
        "rule": (
            "FOR_A_NONNEGATIVE_LOWER_IS_BETTER_BAD_EVENT_METRIC, "
            "AN_INDEPENDENT_SCOPE_COMPLETE_BRAIN_UPPER_BOUND_OF_ZERO "
            "EQUALS_THE_MATHEMATICAL_FLOOR_AND_IS_NONINFERIOR_TO_ANY_TARGET."
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
