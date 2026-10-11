from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.benchmark_output_information_equivalence_gate_v1 import (
    GateError,
    evaluate_route,
)

SCHEMA = "PROJECT_BRAIN_BENCHMARK_EXECUTION_ADMISSION_V1"

BENCHMARK_OR_ACCESS_ACTIONS = {
    "BENCHMARK_EXECUTION",
    "BENCHMARK_PREFLIGHT",
    "PROVIDER_ACCESS_ACQUISITION",
    "OWNER_OR_PLATFORM_RESULT_REQUEST",
    "EXACT_SCORE_RECEIPT_ACQUISITION",
}

PROOF_DEVELOPMENT_ACTIONS = {
    "EQUIVALENCE_PROOF_DEVELOPMENT",
    "STRONGER_CERTIFICATE_DEVELOPMENT",
    "SCOPE_CERTIFICATE_DEVELOPMENT",
    "EXISTING_EVIDENCE_RECOMPUTE",
}


class AdmissionError(ValueError):
    pass


def _fail(reason: str, *, action_kind: str | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "HOLD__FAIL_CLOSED",
        "reason": reason,
        "action_kind": action_kind,
        "execution_admission": False,
        "benchmark_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        return _fail("SPEC_NOT_OBJECT")

    action_kind = spec.get("action_kind")
    if action_kind not in BENCHMARK_OR_ACCESS_ACTIONS | PROOF_DEVELOPMENT_ACTIONS:
        return _fail("ACTION_KIND_INVALID", action_kind=str(action_kind))

    if spec.get("incremental_spend_usd") != 0:
        return _fail("ZERO_INCREMENTAL_SPEND_REQUIRED", action_kind=action_kind)
    if spec.get("uses_target_output_leakage") is not False:
        return _fail("TARGET_OUTPUT_LEAKAGE_NOT_EXCLUDED", action_kind=action_kind)
    if spec.get("reconstructs_private_answers_or_hidden_task_identity") is not False:
        return _fail("PRIVATE_TARGET_RECONSTRUCTION_NOT_EXCLUDED", action_kind=action_kind)

    if action_kind in PROOF_DEVELOPMENT_ACTIONS:
        if spec.get("fresh_target_reality_units") != 0:
            return _fail("PROOF_DEVELOPMENT_MUST_BE_ZERO_TARGET_REALITY", action_kind=action_kind)
        if spec.get("goal_preserving") is not True:
            return _fail("GOAL_PRESERVATION_UNPROVED", action_kind=action_kind)
        return {
            "schema": SCHEMA,
            "status": "ADMIT__ZERO_REALITY_PROOF_DEVELOPMENT",
            "reason": "PROOF_OR_RECOMPUTATION_WORK_MAY_ADVANCE_DECISION_EQUIVALENCE_WITHOUT_CONSUMING_TARGET_REALITY",
            "action_kind": action_kind,
            "execution_admission": True,
            "terminal_credit_authority": False,
            "benchmark_credit_delta": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    terminal = spec.get("terminal_predicate")
    route = spec.get("route")
    try:
        gate = evaluate_route({"terminal_predicate": terminal, "route": route})
    except GateError as exc:
        return _fail(f"BENCHMARK_INFORMATION_GATE:{exc}", action_kind=action_kind)

    if spec.get("current_minimum_information_cut_member") is not True:
        return _fail("NOT_PROVED_MEMBER_OF_CURRENT_MINIMUM_INFORMATION_CUT", action_kind=action_kind)
    if spec.get("route_nondominated_proved") is not True:
        return _fail("ROUTE_NONDominANCE_UNPROVED".upper(), action_kind=action_kind)

    if action_kind == "PROVIDER_ACCESS_ACQUISITION":
        immediate = (
            spec.get("existing_authorized_credential_verified") is True
            or spec.get("self_service_provisioning_verified") is True
        )
        if not immediate:
            return _fail(
                "PROVIDER_ACCESS_NOT_VERIFIED_IMMEDIATELY_EXECUTABLE",
                action_kind=action_kind,
            )

    return {
        "schema": SCHEMA,
        "status": "ADMIT__CURRENT_MINIMUM_DECISION_PRESERVING_ROUTE",
        "reason": "BENCHMARK_OR_ACCESS_ACTION_IS_GATE_VALID_NONDominated_AND_IN_CURRENT_MINIMUM_INFORMATION_CUT".upper(),
        "action_kind": action_kind,
        "execution_admission": True,
        "terminal_type": gate["terminal_type"],
        "route_type": gate["route_type"],
        "information_relation": gate["information_relation"],
        "native_benchmark_deletable_for_this_terminal_predicate": gate[
            "native_benchmark_deletable_for_this_terminal_predicate"
        ],
        "terminal_credit_authority": False,
        "benchmark_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
