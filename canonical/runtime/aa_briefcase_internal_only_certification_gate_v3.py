from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_INTERNAL_ONLY_CERTIFICATION_GATE_V3"
TARGET = "AA-Briefcase v1.1 >= 1822 Elo"
FROZEN_OWNER_MEASURED_REFERENCE = 1821.85
LITERAL_THRESHOLD = 1822.0
REQUIRED_MARGIN = LITERAL_THRESHOLD - FROZEN_OWNER_MEASURED_REFERENCE


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


def _literal_floor_proof(value: Any) -> bool:
    if not _proof(value):
        return False
    lower = value.get("candidate_unrounded_elo_lower_bound")
    return (
        not isinstance(lower, bool)
        and isinstance(lower, (int, float))
        and float(lower) >= LITERAL_THRESHOLD
    )


def _missing(route: Any, names: tuple[str, ...]) -> list[str]:
    if not isinstance(route, Mapping):
        return list(names)
    return [name for name in names if not _proof(route.get(name))]


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise GateError("PAYLOAD_INVALID")
    if payload.get("target") != TARGET:
        raise GateError("TARGET_MISMATCH")
    if payload.get("external_help_allowed") is not False:
        raise GateError("THIS_GATE_IS_INTERNAL_ONLY")

    target_ok = _proof(payload.get("exact_target_identity"))

    precision = payload.get("frozen_reference_precision")
    precision_ok = (
        isinstance(precision, Mapping)
        and precision.get("owner_measured_unrounded_elo") == FROZEN_OWNER_MEASURED_REFERENCE
        and precision.get("literal_threshold_elo") == LITERAL_THRESHOLD
        and precision.get("threshold_changed") is False
        and _proof(precision.get("proof"))
    )

    trace_names = (
        "score_bearing_sufficient_statistic",
        "scorer_implementation_equivariance_or_unique_fit",
    )
    trace_route = payload.get("score_trace_substitution_route")
    trace_missing = _missing(trace_route, trace_names)

    trace_equivalence_bound = (
        isinstance(trace_route, Mapping)
        and _proof(trace_route.get("complete_reference_candidate_trace_equivalence"))
    )
    literal_floor_ok = (
        isinstance(trace_route, Mapping)
        and _literal_floor_proof(trace_route.get("candidate_literal_floor_ge_1822"))
    )

    trace_ok = (
        target_ok
        and precision_ok
        and not trace_missing
        and literal_floor_ok
    )

    top_names = (
        "complete_outcome_superdomain",
        "sound_material_order",
        "brain_support_confined_to_global_top",
        "hidden_evaluator_monotonicity",
        "frozen_1822_score_monotonicity",
    )
    top_missing = _missing(payload.get("top_support_route"), top_names)
    top_ok = target_ok and not top_missing

    passed = trace_ok or top_ok

    parity_only = (
        target_ok
        and precision_ok
        and not trace_missing
        and trace_equivalence_bound
        and not literal_floor_ok
    )

    return {
        "schema": SCHEMA,
        "status": "PASS_INTERNAL_ONLY" if passed else "OPEN_INTERNAL_ONLY",
        "pass": passed,
        "accepted_route": (
            "QUANTITATIVE_SCORE_TRACE"
            if trace_ok
            else "UNIVERSAL_TOP_SUPPORT"
            if top_ok
            else None
        ),
        "target_identity_missing": not target_ok,
        "frozen_reference_precision_missing": not precision_ok,
        "score_trace_substitution_missing": trace_missing,
        "trace_equivalence_bound": trace_equivalence_bound,
        "trace_equivalence_is_reference_parity_only": parity_only,
        "candidate_literal_floor_ge_1822_missing": not literal_floor_ok,
        "top_support_missing": top_missing,
        "frozen_owner_measured_reference_elo": FROZEN_OWNER_MEASURED_REFERENCE,
        "literal_threshold_elo": LITERAL_THRESHOLD,
        "minimum_required_improvement_over_exact_reference": REQUIRED_MARGIN,
        "external_help_required_by_gate": False,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
