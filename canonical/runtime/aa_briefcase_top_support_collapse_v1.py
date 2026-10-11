from __future__ import annotations

from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_TOP_SUPPORT_COLLAPSE_V1"


class CollapseError(ValueError):
    pass


def indicator_prefers(outcome: str, preferred: str) -> int:
    return 1 if outcome == preferred else 0


def dominates_under_all_indicators(candidate: str, other: str, outcomes: Iterable[str]) -> bool:
    ys = list(outcomes)
    if candidate not in ys or other not in ys:
        raise CollapseError("OUTCOME_NOT_IN_DOMAIN")
    for preferred in ys:
        if indicator_prefers(candidate, preferred) < indicator_prefers(other, preferred):
            return False
    return True


def universal_top_elements(outcomes: Iterable[str]) -> list[str]:
    ys = list(outcomes)
    if not ys:
        raise CollapseError("EMPTY_OUTCOME_DOMAIN")
    if len(ys) != len(set(ys)):
        raise CollapseError("DUPLICATE_OUTCOME")
    return [
        candidate
        for candidate in ys
        if all(dominates_under_all_indicators(candidate, other, ys) for other in ys)
    ]


def evaluate_aa_top_support_route(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise CollapseError("PAYLOAD_INVALID")
    if payload.get("benchmark") != "AA-Briefcase" or payload.get("version") != "1.1":
        raise CollapseError("TARGET_MISMATCH")
    if payload.get("scope_complete_public_superdomain") is not True:
        raise CollapseError("SUPERDOMAIN_NOT_BOUND")

    hidden_predicate_class_restricted = (
        payload.get("hidden_predicate_class_soundly_restricted") is True
    )
    material_order_complete = payload.get("material_order_complete") is True
    brain_top_support = payload.get("brain_global_top_support_proved") is True
    judge_monotonicity = payload.get("judge_monotonicity_proved") is True
    score_monotonicity = payload.get("frozen_score_monotonicity_proved") is True

    if not hidden_predicate_class_restricted:
        demo = universal_top_elements(["OUTCOME_A", "OUTCOME_B"])
        return {
            "schema": SCHEMA,
            "status": "COLLAPSE_TO_OBSERVATIONAL_EQUIVALENCE",
            "pass": False,
            "universal_top_elements_in_two_outcome_indicator_class": demo,
            "reason": (
                "The current AA public-interface superdomain represents hidden rubric "
                "predicates opaquely and allows arbitrary finite binary predicates. "
                "That class contains indicator predicates separating any two distinct "
                "outcomes. Hence the induced universal material preorder has no "
                "nontrivial cross-outcome dominance: x>=y for every hidden predicate "
                "only when x=y."
            ),
            "required_reopen": (
                "A sound restriction of the actual private rubric/judge utility class "
                "that excludes arbitrary separating predicates."
            ),
            "threshold_1822_proved": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
        }

    missing = []
    if not material_order_complete:
        missing.append("SOUND_COMPLETE_MATERIAL_ORDER")
    if not brain_top_support:
        missing.append("BRAIN_GLOBAL_TOP_SUPPORT")
    if not judge_monotonicity:
        missing.append("HIDDEN_JUDGE_MONOTONICITY")
    if not score_monotonicity:
        missing.append("FROZEN_1822_SCORE_MONOTONICITY")

    return {
        "schema": SCHEMA,
        "status": "PASS_TOP_SUPPORT_PREMISES" if not missing else "OPEN_RESTRICTED_TOP_SUPPORT",
        "pass": not missing,
        "missing": missing,
        "threshold_1822_proved": not missing,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
