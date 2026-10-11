from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_INTERNAL_ONLY_CERTIFICATION_GATE_V2"


class GateError(ValueError):
    pass


def _proof(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("verified") is True
        and value.get("scope_complete") is True
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and isinstance(value.get("git_blob_sha"), str)
        and len(value.get("git_blob_sha")) == 40
    )


def _missing(route: Any, names: tuple[str, ...]) -> list[str]:
    if not isinstance(route, Mapping):
        return list(names)
    return [name for name in names if not _proof(route.get(name))]


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise GateError("PAYLOAD_INVALID")
    if payload.get("target") != "AA-Briefcase v1.1 >= 1822 Elo":
        raise GateError("TARGET_MISMATCH")
    if payload.get("external_help_allowed") is not False:
        raise GateError("THIS_GATE_IS_INTERNAL_ONLY")

    target_ok = _proof(payload.get("exact_target_identity"))

    trace_names = (
        "score_bearing_sufficient_statistic",
        "complete_reference_candidate_trace_equivalence",
        "scorer_implementation_equivariance_or_unique_fit",
        "frozen_reference_1822",
    )
    top_names = (
        "complete_outcome_superdomain",
        "sound_material_order",
        "brain_support_confined_to_global_top",
        "hidden_evaluator_monotonicity",
        "frozen_1822_score_monotonicity",
    )

    trace_missing = _missing(payload.get("score_trace_substitution_route"), trace_names)
    top_missing = _missing(payload.get("top_support_route"), top_names)

    trace_ok = not trace_missing
    top_ok = not top_missing
    passed = target_ok and (trace_ok or top_ok)

    return {
        "schema": SCHEMA,
        "status": "PASS_INTERNAL_ONLY" if passed else "OPEN_INTERNAL_ONLY",
        "pass": passed,
        "accepted_route": (
            "SCORE_TRACE_SUBSTITUTION"
            if target_ok and trace_ok
            else "UNIVERSAL_TOP_SUPPORT"
            if target_ok and top_ok
            else None
        ),
        "target_identity_missing": not target_ok,
        "score_trace_substitution_missing": trace_missing,
        "top_support_missing": top_missing,
        "external_help_required_by_gate": False,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
