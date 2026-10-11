from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_RUBRIC_ONLY_BYPASS_GATE_V1"


class RubricBypassError(ValueError):
    pass


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise RubricBypassError("PAYLOAD_INVALID")
    if payload.get("target") != "AA-Briefcase v1.1 >= 1822 Elo":
        raise RubricBypassError("TARGET_MISMATCH")

    public_three_scope_semantics_bound = (
        payload.get("public_three_scope_semantics_bound") is True
    )
    rubric_only = payload.get("rubric_only_certificate") is True
    aggregate_lower_bound = payload.get(
        "sound_rubric_only_headline_elo_lower_bound_ge_1822"
    ) is True
    aq_bound = payload.get("analytical_quality_score_bearing_state_bound") is True
    presentation_bound = payload.get(
        "presentation_score_bearing_state_bound"
    ) is True

    if not public_three_scope_semantics_bound:
        raise RubricBypassError("PUBLIC_THREE_SCOPE_SEMANTICS_UNBOUND")

    if rubric_only and not aggregate_lower_bound:
        return {
            "schema": SCHEMA,
            "status": "REJECT_RUBRIC_ONLY_BYPASS",
            "pass": False,
            "reason": (
                "AA-Briefcase headline Elo is score-bearing across rubric, "
                "analytical-quality, and presentation scopes. Rubric evidence alone "
                "does not entail the frozen 1822 headline without a separately proved "
                "headline lower-bound theorem."
            ),
            "missing": [
                "SOUND_RUBRIC_ONLY_HEADLINE_ELO_LOWER_BOUND_GE_1822",
                "OR_SCORE_BEARING_AQ_AND_PRESENTATION_RELATION"
            ],
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
        }

    if rubric_only and aggregate_lower_bound:
        return {
            "schema": SCHEMA,
            "status": "RUBRIC_ONLY_BYPASS_THEOREM_REQUIRED_UPSTREAM",
            "pass": False,
            "reason": (
                "A caller assertion is not proof. The claimed aggregate lower-bound "
                "must be admitted as a content-addressed independently verified proof."
            ),
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
        }

    if aq_bound and presentation_bound:
        return {
            "schema": SCHEMA,
            "status": "THREE_SCOPE_INFORMATION_PRESENT__CONTINUE_SCORE_TRACE_ROUTE",
            "pass": False,
            "reason": "Use the canonical score-bearing trace substitution gate.",
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "OPEN_SCORE_BEARING_SCOPE_INFORMATION",
        "pass": False,
        "missing": [
            name
            for name, present in (
                ("ANALYTICAL_QUALITY_SCORE_BEARING_STATE", aq_bound),
                ("PRESENTATION_SCORE_BEARING_STATE", presentation_bound),
            )
            if not present
        ],
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
