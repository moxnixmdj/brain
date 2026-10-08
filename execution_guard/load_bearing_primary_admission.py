from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LOAD_BEARING_PRIMARY_ADMISSION_V1"


class LoadBearingAdmissionError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _ids(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise LoadBearingAdmissionError(name + "_NOT_LIST")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise LoadBearingAdmissionError(name + "_INVALID_ITEM")
    out = tuple(sorted(set(x.strip() for x in value)))
    if len(out) != len(value):
        raise LoadBearingAdmissionError(name + "_DUPLICATE")
    return out


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise LoadBearingAdmissionError(name + "_INVALID")
    try:
        out = Fraction(str(value))
    except Exception as exc:
        raise LoadBearingAdmissionError(name + "_INVALID") from exc
    if out < 0:
        raise LoadBearingAdmissionError(name + "_NEGATIVE")
    return out


def admission_errors(
    intent: Any,
    current_open_obligations: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    open_ids = {x for x in current_open_obligations if isinstance(x, str) and x}
    if not open_ids:
        return errors
    if not isinstance(intent, Mapping):
        return ["LOAD_BEARING_INTENT_INVALID"]

    binding = intent.get("load_bearing_primary")
    if not isinstance(binding, Mapping):
        return ["LOAD_BEARING_PRIMARY_BINDING_MISSING"]

    try:
        direct = set(_ids(binding.get("open_obligation_ids"), "LOAD_BEARING_OPEN_OBLIGATIONS"))
        gaps = set(
            _ids(
                binding.get("constructive_gap_for_open_obligation_ids"),
                "LOAD_BEARING_CONSTRUCTIVE_GAPS",
            )
        )
    except LoadBearingAdmissionError as exc:
        return [str(exc)]

    scope_complete = binding.get("scope_complete_discharge") is True
    if not direct and not gaps and not scope_complete:
        errors.append("LOAD_BEARING_CAUSAL_PATH_MISSING")

    unknown = sorted((direct | gaps) - open_ids)
    if unknown:
        errors.append("LOAD_BEARING_TARGET_NOT_CURRENT_OPEN:" + ",".join(unknown))

    try:
        discharge = _fraction(
            binding.get("expected_obligation_discharge_lcb", 0),
            "LOAD_BEARING_EXPECTED_DISCHARGE_LCB",
        )
        unlock = _fraction(
            binding.get("expected_obligation_unlock_lcb", 0),
            "LOAD_BEARING_EXPECTED_UNLOCK_LCB",
        )
        success = _fraction(
            binding.get("success_probability_lcb", 0),
            "LOAD_BEARING_SUCCESS_PROBABILITY_LCB",
        )
        wall = _fraction(
            binding.get("wall_clock_cost_ub", 0),
            "LOAD_BEARING_WALL_CLOCK_COST_UB",
        )
        if success > 1:
            errors.append("LOAD_BEARING_SUCCESS_PROBABILITY_LCB_GT_ONE")
        if wall <= 0:
            errors.append("LOAD_BEARING_WALL_CLOCK_COST_UB_NOT_POSITIVE")
        if (discharge + unlock) * success <= 0:
            errors.append("LOAD_BEARING_EXPECTED_YIELD_NOT_POSITIVE")
    except LoadBearingAdmissionError as exc:
        errors.append(str(exc))

    if intent.get("highest_leverage_now") is not True:
        errors.append("LOAD_BEARING_NOT_ASSERTED_HIGHEST_LEVERAGE")

    return sorted(set(errors))
