"""Fail-closed reducer for MysteryMechanism represented-scope intrinsic noninferiority."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

TASK_COUNT = 222
INTRINSIC_OPUS_PUBLIC_PERCENT = Decimal("49.10")
DEPLOYED_OPUS_PUBLIC_PERCENT = Decimal("49.55")


def displayed_percent(successes: int, task_count: int = TASK_COUNT) -> Decimal:
    if not isinstance(successes, int) or isinstance(successes, bool):
        raise TypeError("successes must be an integer")
    if not isinstance(task_count, int) or isinstance(task_count, bool):
        raise TypeError("task_count must be an integer")
    if task_count <= 0 or not 0 <= successes <= task_count:
        raise ValueError("invalid success/task count")
    return (Decimal(100) * Decimal(successes) / Decimal(task_count)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def unique_success_count(percent: Decimal | str, task_count: int = TASK_COUNT) -> int:
    target = Decimal(str(percent))
    matches = [k for k in range(task_count + 1) if displayed_percent(k, task_count) == target]
    if len(matches) != 1:
        raise ValueError("displayed percentage does not uniquely identify a success count")
    return matches[0]


INTRINSIC_OPUS_SUCCESS_COUNT = unique_success_count(INTRINSIC_OPUS_PUBLIC_PERCENT)
DEPLOYED_OPUS_SUCCESS_COUNT = unique_success_count(DEPLOYED_OPUS_PUBLIC_PERCENT)


@dataclass(frozen=True)
class CertificateResult:
    passed: bool
    route: str
    reason: str
    required_successes: int = INTRINSIC_OPUS_SUCCESS_COUNT


def _bound_population(p: Mapping[str, Any]) -> bool:
    return p.get("task_count") == TASK_COUNT and p.get("same_private_population") is True


def _require_true(p: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if p.get(key) is not True:
            return key
    return None


def evaluate_certificate(p: Mapping[str, Any]) -> CertificateResult:
    route = p.get("route")
    if route == "MATCHED_COUNT":
        if not _bound_population(p):
            return CertificateResult(False, route, "population_not_exactly_bound")
        missing = _require_true(p, (
            "authentic_receipt", "same_task_contract", "same_scorer",
            "no_opaque_target_capability_provider", "independently_verified",
        ))
        if missing:
            return CertificateResult(False, route, f"missing_or_false:{missing}")
        successes = p.get("brain_successes")
        if not isinstance(successes, int) or isinstance(successes, bool) or not 0 <= successes <= TASK_COUNT:
            return CertificateResult(False, route, "invalid_brain_success_count")
        if successes < INTRINSIC_OPUS_SUCCESS_COUNT:
            return CertificateResult(False, route, "brain_success_count_below_intrinsic_reference")
        return CertificateResult(True, route, "matched_count_noninferiority_proved")

    if route == "THRESHOLD_MASS":
        if not _bound_population(p):
            return CertificateResult(False, route, "population_not_exactly_bound")
        missing = _require_true(p, (
            "class_membership_mass_scope_complete", "brain_universal_success_on_certified_class",
            "same_task_contract", "same_scorer", "independently_verified",
        ))
        if missing:
            return CertificateResult(False, route, f"missing_or_false:{missing}")
        mass = p.get("guaranteed_private_success_mass")
        if not isinstance(mass, int) or isinstance(mass, bool) or not 0 <= mass <= TASK_COUNT:
            return CertificateResult(False, route, "invalid_guaranteed_private_success_mass")
        if mass < INTRINSIC_OPUS_SUCCESS_COUNT:
            return CertificateResult(False, route, "certified_private_mass_below_intrinsic_reference")
        return CertificateResult(True, route, "threshold_mass_noninferiority_proved")

    if route == "SUCCESS_SET_DOMINANCE":
        if not _bound_population(p):
            return CertificateResult(False, route, "population_not_exactly_bound")
        missing = _require_true(p, (
            "intrinsic_opus_success_set_content_bound", "brain_success_set_content_bound",
            "opus_success_set_subset_of_brain_success_set", "same_task_contract",
            "same_scorer", "independently_verified",
        ))
        if missing:
            return CertificateResult(False, route, f"missing_or_false:{missing}")
        if p.get("intrinsic_opus_success_count") != INTRINSIC_OPUS_SUCCESS_COUNT:
            return CertificateResult(False, route, "intrinsic_opus_success_count_not_bound_to_109")
        return CertificateResult(True, route, "taskwise_success_set_dominance_proved")

    return CertificateResult(False, str(route), "unknown_or_missing_route")
