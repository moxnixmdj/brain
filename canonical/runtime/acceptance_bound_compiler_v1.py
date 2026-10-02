"""Fail-closed conservative acceptance bound compiler.

Purpose:
- determine whether a frozen fixed-bar acceptance result can be forced from a
  strict subset of executable observations;
- assign worst-case values to unavailable/unexecuted slots;
- expose exact pass/fail locks without extrapolation.

This module never grants capability/family credit by itself.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_BOUND_COMPILER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "metric_type": None,
        "decision": "UNRESOLVED",
        "proof_route_ready": False,
        "execution_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _int(v: Any) -> int | None:
    return None if isinstance(v, bool) or not isinstance(v, int) else v


def _dec(v: Any) -> Decimal | None:
    if isinstance(v, bool) or not isinstance(v, (int, float, str, Decimal)):
        return None
    try:
        d = Decimal(str(v))
    except Exception:
        return None
    return d if d.is_finite() else None


def _ceil_decimal(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_CEILING))


def _binary_rate(spec: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    total = _int(spec.get("total_slots"))
    executable = _int(spec.get("executable_slots"))
    successes = _int(spec.get("observed_successes", 0))
    failures = _int(spec.get("observed_failures", 0))
    threshold = _dec(spec.get("threshold_percent"))
    if total is None or total <= 0:
        errors.append("TOTAL_SLOTS_INVALID")
    if executable is None or executable < 0:
        errors.append("EXECUTABLE_SLOTS_INVALID")
    if successes is None or successes < 0:
        errors.append("OBSERVED_SUCCESSES_INVALID")
    if failures is None or failures < 0:
        errors.append("OBSERVED_FAILURES_INVALID")
    if threshold is None or threshold < 0 or threshold > 100:
        errors.append("THRESHOLD_PERCENT_INVALID")
    if errors:
        return _fail(*errors)
    assert total is not None and executable is not None and successes is not None and failures is not None and threshold is not None
    if executable > total:
        return _fail("EXECUTABLE_SLOTS_EXCEED_TOTAL")
    if successes + failures > executable:
        return _fail("OBSERVATIONS_EXCEED_EXECUTABLE_SLOTS")

    required = _ceil_decimal((threshold * Decimal(total)) / Decimal(100))
    remaining_exec = executable - successes - failures
    best_possible_successes = successes + remaining_exec
    worst_case_successes = successes

    lower_rate = (Decimal(worst_case_successes) * Decimal(100)) / Decimal(total)
    upper_rate = (Decimal(best_possible_successes) * Decimal(100)) / Decimal(total)
    feasible = executable >= required
    if successes >= required:
        decision = "PASS_LOCKED"
    elif best_possible_successes < required:
        decision = "FAIL_LOCKED"
    else:
        decision = "UNRESOLVED"

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "metric_type": "BINARY_RATE",
        "decision": decision,
        "proof_route_ready": feasible,
        "execution_authority": False,
        "total_slots": total,
        "executable_slots": executable,
        "unavailable_slots": total - executable,
        "observed_successes": successes,
        "observed_failures": failures,
        "remaining_executable_slots": remaining_exec,
        "threshold_percent": str(threshold),
        "required_successes": required,
        "conservative_lower_bound_percent": str(lower_rate),
        "optimistic_upper_bound_percent": str(upper_rate),
        "pass_lock_rule": f"OBSERVED_SUCCESSES>={required}",
        "fail_lock_rule": f"OBSERVED_SUCCESSES+REMAINING_EXECUTABLE_SLOTS<{required}",
        "unknown_and_unavailable_slot_value": 0,
        "rule": "NO_EXTRAPOLATION__UNAVAILABLE_UNEXECUTED_FAILED_OR_CONTAMINATED_SLOTS_TAKE_WORST_CASE_ZERO",
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _bounded_mean(spec: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    total = _int(spec.get("total_items"))
    observed = _int(spec.get("observed_items", 0))
    known_sum = _dec(spec.get("known_sum", 0))
    item_min = _dec(spec.get("item_min"))
    item_max = _dec(spec.get("item_max"))
    threshold = _dec(spec.get("threshold"))
    direction = spec.get("direction")
    if total is None or total <= 0:
        errors.append("TOTAL_ITEMS_INVALID")
    if observed is None or observed < 0:
        errors.append("OBSERVED_ITEMS_INVALID")
    if known_sum is None:
        errors.append("KNOWN_SUM_INVALID")
    if item_min is None or item_max is None or item_min > item_max:
        errors.append("ITEM_BOUNDS_INVALID")
    if threshold is None:
        errors.append("THRESHOLD_INVALID")
    if direction not in {"HIGHER_IS_BETTER", "LOWER_IS_BETTER"}:
        errors.append("DIRECTION_INVALID")
    if errors:
        return _fail(*errors)
    assert total is not None and observed is not None and known_sum is not None and item_min is not None and item_max is not None and threshold is not None
    if observed > total:
        return _fail("OBSERVED_ITEMS_EXCEED_TOTAL")
    remaining = total - observed
    lower = (known_sum + Decimal(remaining) * item_min) / Decimal(total)
    upper = (known_sum + Decimal(remaining) * item_max) / Decimal(total)

    if direction == "HIGHER_IS_BETTER":
        decision = "PASS_LOCKED" if lower >= threshold else ("FAIL_LOCKED" if upper < threshold else "UNRESOLVED")
    else:
        decision = "PASS_LOCKED" if upper <= threshold else ("FAIL_LOCKED" if lower > threshold else "UNRESOLVED")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "metric_type": "BOUNDED_MEAN",
        "decision": decision,
        "proof_route_ready": True,
        "execution_authority": False,
        "total_items": total,
        "observed_items": observed,
        "remaining_items": remaining,
        "known_sum": str(known_sum),
        "item_min": str(item_min),
        "item_max": str(item_max),
        "threshold": str(threshold),
        "direction": direction,
        "conservative_lower_bound": str(lower),
        "conservative_upper_bound": str(upper),
        "rule": "UNKNOWN_ITEMS_USE_GLOBAL_WORST_CASE_BOUNDS__NONLINEAR_OR_UNPROVEN_METRIC_TRANSFORMS_FORBIDDEN",
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if spec.get("metric_semantics_frozen") is not True:
        return _fail("METRIC_SEMANTICS_NOT_FROZEN")
    if spec.get("population_frozen") is not True:
        return _fail("POPULATION_NOT_FROZEN")
    if spec.get("worst_case_assignment_admissible") is not True:
        return _fail("WORST_CASE_ASSIGNMENT_NOT_PROVEN_ADMISSIBLE")

    metric = spec.get("metric_type")
    if metric == "BINARY_RATE":
        return _binary_rate(spec)
    if metric == "BOUNDED_MEAN":
        return _bounded_mean(spec)
    return _fail("UNSUPPORTED_METRIC_TYPE")
