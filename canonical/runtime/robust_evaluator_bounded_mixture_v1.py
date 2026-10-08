"""Exact robust bounds for a bounded mixture of uncertain evaluator components.

This module does not discover evaluator semantics. It answers a conditional question:
given exact interval bounds on each component's Brain-minus-target delta and exact
lower/upper bounds on nonnegative mixture weights summing to one, what are the
worst and best possible aggregate deltas over that uncertainty superset?

If the worst-case delta is >= 0, Brain is noninferior for every admissible mixture.
If the best-case delta is < 0, Brain is inferior for every admissible mixture.
Otherwise the result is UNKNOWN.

All arithmetic is exact Fraction arithmetic. Semantic validity of the supplied
bounds requires independent proof; this runtime grants no terminal authority.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping


class RobustMixtureError(ValueError):
    pass


def _f(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise RobustMixtureError(f"{label}_BOOL_FORBIDDEN")
    try:
        return Fraction(str(value))
    except Exception as exc:
        raise RobustMixtureError(f"{label}_INVALID:{value}") from exc


def _parse(task: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = task.get("components")
    if not isinstance(rows, list) or not rows:
        raise RobustMixtureError("COMPONENTS_REQUIRED")
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("id"):
            raise RobustMixtureError("COMPONENT_INVALID")
        cid = str(row["id"])
        if cid in seen:
            raise RobustMixtureError(f"DUPLICATE_COMPONENT:{cid}")
        seen.add(cid)
        dl = _f(row.get("delta_lower"), f"{cid}_DELTA_LOWER")
        du = _f(row.get("delta_upper"), f"{cid}_DELTA_UPPER")
        wl = _f(row.get("weight_lower"), f"{cid}_WEIGHT_LOWER")
        wu = _f(row.get("weight_upper"), f"{cid}_WEIGHT_UPPER")
        if dl > du:
            raise RobustMixtureError(f"DELTA_INTERVAL_REVERSED:{cid}")
        if wl < 0 or wu < 0 or wl > wu or wu > 1:
            raise RobustMixtureError(f"WEIGHT_BOUNDS_INVALID:{cid}")
        out.append({"id": cid, "dl": dl, "du": du, "wl": wl, "wu": wu})
    if sum((r["wl"] for r in out), Fraction(0)) > 1:
        raise RobustMixtureError("WEIGHT_LOWER_SUM_EXCEEDS_ONE")
    if sum((r["wu"] for r in out), Fraction(0)) < 1:
        raise RobustMixtureError("WEIGHT_UPPER_SUM_BELOW_ONE")
    return out


def _extreme(rows: list[dict[str, Any]], *, use_upper_delta: bool) -> tuple[Fraction, list[dict[str, str]]]:
    # For max, use each component's largest admissible delta and allocate residual
    # weight to the largest deltas. For min, use lower deltas and allocate to smallest.
    key = "du" if use_upper_delta else "dl"
    weights = {r["id"]: r["wl"] for r in rows}
    remaining = Fraction(1) - sum(weights.values(), Fraction(0))
    ordered = sorted(rows, key=lambda r: (r[key], r["id"]), reverse=use_upper_delta)
    for r in ordered:
        if remaining <= 0:
            break
        room = r["wu"] - weights[r["id"]]
        take = min(room, remaining)
        weights[r["id"]] += take
        remaining -= take
    if remaining != 0:
        raise RobustMixtureError("INFEASIBLE_BOUNDED_SIMPLEX")
    total = sum((weights[r["id"]] * r[key] for r in rows), Fraction(0))
    witness = [
        {
            "id": r["id"],
            "weight": str(weights[r["id"]]),
            "delta": str(r[key]),
        }
        for r in sorted(rows, key=lambda x: x["id"])
    ]
    return total, witness


def solve(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise RobustMixtureError("TASK_INVALID")
    rows = _parse(task)
    lower, lower_witness = _extreme(rows, use_upper_delta=False)
    upper, upper_witness = _extreme(rows, use_upper_delta=True)

    if lower >= 0:
        verdict = "PASS__ROBUST_NONINFERIOR"
    elif upper < 0:
        verdict = "FAIL__ROBUSTLY_INFERIOR"
    else:
        verdict = "UNKNOWN__IDENTIFIED_INTERVAL_STRADDLES_ZERO"

    sensitivity = [
        {
            "id": r["id"],
            "delta_width": str(r["du"] - r["dl"]),
            "max_direct_interval_contribution": str(r["wu"] * (r["du"] - r["dl"])),
        }
        for r in sorted(rows, key=lambda x: (x["wu"] * (x["du"] - x["dl"]), x["id"]), reverse=True)
    ]

    return {
        "schema": "PROJECT_BRAIN_ROBUST_EVALUATOR_BOUNDED_MIXTURE_RESULT_V1",
        "status": verdict,
        "identified_delta_interval": {"lower": str(lower), "upper": str(upper)},
        "lower_bound_witness": lower_witness,
        "upper_bound_witness": upper_witness,
        "decision_sensitive_components_ranked_by_safe_direct_width_bound": sensitivity,
        "theorem": "BOUNDED_MIXTURE_ROBUST_INTERVAL_OVER_INDEPENDENT_COMPONENT_DELTA_AND_WEIGHT_BOUNDS",
        "semantic_premise_verified_by_this_runtime": False,
        "uncertainty_model_note": "INDEPENDENT_INTERVAL_PRODUCT_SET_IS_A_CONSERVATIVE_SUPERSET_WHEN_TRUE_DEPENDENCIES_ARE_UNKNOWN",
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
