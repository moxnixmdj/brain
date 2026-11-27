"""Fail-closed premise binder for the behavioral observational quotient.

This module does not prove Brain performance. It verifies that the canonical
terminal target is explicitly behavioral rather than implementation-identical,
and that the frozen capability envelope is well-formed enough for the
observational-quotient theorem to apply.

The theorem itself is extensional: internal states/channels that induce the
same externally observable causal behavior are in the same behavioral
equivalence class. Enumerating those hidden channels is therefore unnecessary
for *target-domain identity*. Performance/noninferiority remains a separate
obligation over the observable behavioral domain.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_BEHAVIORAL_OBSERVATIONAL_QUOTIENT_V1"
TARGET_RULE = "USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION"
TARGET_MODEL = "Claude Opus 5.5"


class QuotientError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuotientError(label + "_INVALID")
    return value.strip()


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise QuotientError(label + "_INVALID")
    return list(value)


def verify_behavioral_target_contract(
    target_envelope: Mapping[str, Any],
    intrinsic_boundary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the canonical premises required by the observational quotient.

    PASS means only:
    * the terminal target explicitly identifies useful behavior, not hidden
      implementation identity, as the object of comparison;
    * every frozen family has a non-empty useful-behavior description;
    * the declared family count is internally consistent; and
    * when supplied, the intrinsic boundary still excludes external/fallback
      computation from intrinsic Opus credit.

    PASS does not establish that the 19-family partition is exhaustive, that
    Brain dominates the behavioral domain, or that any acceptance predicate is
    proved.
    """
    try:
        if not isinstance(target_envelope, Mapping):
            raise QuotientError("TARGET_ENVELOPE_NOT_OBJECT")

        if _token(target_envelope.get("target_model"), "TARGET_MODEL") != TARGET_MODEL:
            raise QuotientError("TARGET_MODEL_MISMATCH")
        if _token(target_envelope.get("target_rule"), "TARGET_RULE") != TARGET_RULE:
            raise QuotientError("TARGET_RULE_NOT_BEHAVIORAL")

        families = _sequence(target_envelope.get("families"), "FAMILIES")
        if not families:
            raise QuotientError("FAMILIES_EMPTY")

        ids: list[str] = []
        for i, raw in enumerate(families):
            if not isinstance(raw, Mapping):
                raise QuotientError(f"FAMILY_{i}_NOT_OBJECT")
            fid = _token(raw.get("id"), f"FAMILY_{i}_ID")
            _token(raw.get("useful_behavior"), f"FAMILY_{i}_USEFUL_BEHAVIOR")
            ids.append(fid)

        if len(ids) != len(set(ids)):
            raise QuotientError("FAMILY_ID_DUPLICATE")

        declared_count = target_envelope.get("target_family_count")
        if not isinstance(declared_count, int) or isinstance(declared_count, bool):
            raise QuotientError("TARGET_FAMILY_COUNT_INVALID")
        if declared_count != len(families):
            raise QuotientError("TARGET_FAMILY_COUNT_MISMATCH")

        boundary_checks = {
            "provided": intrinsic_boundary is not None,
            "actor_projection_present": None,
            "external_executor_excluded": None,
            "fallback_excluded": None,
        }
        if intrinsic_boundary is not None:
            if not isinstance(intrinsic_boundary, Mapping):
                raise QuotientError("INTRINSIC_BOUNDARY_NOT_OBJECT")
            normal = intrinsic_boundary.get("causal_normal_form")
            if not isinstance(normal, Mapping):
                raise QuotientError("CAUSAL_NORMAL_FORM_MISSING")
            excluded = {
                str(x)
                for x in _sequence(
                    normal.get("excluded_from_intrinsic_credit_without_separate_causal_evidence"),
                    "EXCLUDED_INTRINSIC_CREDIT",
                )
            }
            projection = _token(
                normal.get("intrinsic_target_projection"),
                "INTRINSIC_TARGET_PROJECTION",
            )
            external_ok = any("EXTERNAL" in x and "EXECUTOR" in x for x in excluded)
            fallback_ok = any("FALLBACK" in x for x in excluded)
            if not external_ok:
                raise QuotientError("EXTERNAL_EXECUTOR_NOT_EXCLUDED")
            if not fallback_ok:
                raise QuotientError("FALLBACK_NOT_EXCLUDED")
            boundary_checks = {
                "provided": True,
                "actor_projection_present": bool(projection),
                "external_executor_excluded": True,
                "fallback_excluded": True,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "target_model": TARGET_MODEL,
            "target_rule": TARGET_RULE,
            "family_count": len(families),
            "family_ids": ids,
            "boundary_checks": boundary_checks,
            "theorem": "BEHAVIORAL_TARGET_FACTORS_THROUGH_OBSERVATIONAL_EQUIVALENCE",
            "internal_channel_enumeration_required_for_behavioral_target_identity": False,
            "arbitrary_hidden_state_compatible_with_domain_coverage": True,
            "performance_noninferiority_proved": False,
            "family_partition_exhaustive_proved": False,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "internal_channel_enumeration_required_for_behavioral_target_identity": None,
            "performance_noninferiority_proved": False,
            "family_partition_exhaustive_proved": False,
            "acceptance_credit_delta": 0,
        }


def observational_equivalent(
    left_distribution: Mapping[str, Any],
    right_distribution: Mapping[str, Any],
) -> bool:
    """Exact finite witness for observational equivalence.

    Keys denote complete observable trace classes and values their exact
    probabilities/weights. Hidden implementation state is intentionally absent.
    """
    return dict(left_distribution) == dict(right_distribution)
