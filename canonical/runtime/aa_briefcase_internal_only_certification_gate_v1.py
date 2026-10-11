from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_INTERNAL_ONLY_CERTIFICATION_GATE_V1"


class GateError(ValueError):
    pass


def _is_bound_proof(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("verified") is True
        and value.get("scope_complete") is True
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and isinstance(value.get("git_blob_sha"), str)
        and len(value.get("git_blob_sha")) == 40
    )


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise GateError("PAYLOAD_INVALID")
    if payload.get("target") != "AA-Briefcase v1.1 >= 1822 Elo":
        raise GateError("TARGET_MISMATCH")
    if payload.get("external_help_allowed") is not False:
        raise GateError("THIS_GATE_IS_INTERNAL_ONLY")

    exact_target = _is_bound_proof(payload.get("exact_target_identity"))

    obs = payload.get("observational_equivalence_route")
    obs_ok = (
        isinstance(obs, Mapping)
        and _is_bound_proof(obs.get("whole_hidden_scope_equivalence"))
        and _is_bound_proof(obs.get("frozen_1822_score_implication"))
    )

    top = payload.get("top_support_route")
    top_ok = (
        isinstance(top, Mapping)
        and _is_bound_proof(top.get("complete_outcome_superdomain"))
        and _is_bound_proof(top.get("sound_material_order"))
        and _is_bound_proof(top.get("brain_support_confined_to_global_top"))
        and _is_bound_proof(top.get("hidden_evaluator_monotonicity"))
        and _is_bound_proof(top.get("frozen_1822_score_monotonicity"))
    )

    passed = exact_target and (obs_ok or top_ok)
    missing = []
    if not exact_target:
        missing.append("EXACT_TARGET_IDENTITY")
    if not obs_ok:
        missing.append("OBSERVATIONAL_EQUIVALENCE_ROUTE")
    if not top_ok:
        missing.append("UNIVERSAL_TOP_SUPPORT_ROUTE")

    return {
        "schema": SCHEMA,
        "status": "PASS_INTERNAL_ONLY" if passed else "OPEN_INTERNAL_ONLY",
        "pass": passed,
        "accepted_route": (
            "OBSERVATIONAL_EQUIVALENCE"
            if exact_target and obs_ok
            else "UNIVERSAL_TOP_SUPPORT"
            if exact_target and top_ok
            else None
        ),
        "missing": [] if passed else missing,
        "external_help_required_by_gate": False,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
