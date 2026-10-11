"""Execute the objective subset of a lossless raw-task acceptance contract.

This controller composes existing Brain-owned acceptance machinery:
- lossless_raw_task_contract_v1 preserves every non-whitespace source segment;
- raw_task_acceptance_residual_localizer_v1 discovers only already-supported,
  source-grounded objective verifier routes;
- instruction_constraint_compiler_v1 executes explicit response-form constraints;
- typed_acceptance_program_v1 executes controlled source-aligned field predicates.

It never treats route availability, existing tests, or builder success as complete
acceptance. Any raw source segment without a sound objective route remains an
explicit semantic residual and blocks acceptance.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.instruction_constraint_compiler_v1 import (
    ConstraintError,
    compile_constraints,
    validate_response,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_task_acceptance_residual_localizer_v1 import localize
from canonical.runtime.typed_acceptance_program_v1 import verify as verify_typed_program

SCHEMA = "PROJECT_BRAIN_RAW_TASK_OBJECTIVE_ACCEPTANCE_EXECUTOR_V1"
CAPABILITY_ID = "task.acceptance.objective.lossless.v1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0


class ObjectiveAcceptanceError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise ObjectiveAcceptanceError("CANDIDATE_NOT_OBJECT")
    allowed = {"response_text", "fields", "evidence"}
    extra = sorted(set(candidate) - allowed)
    if extra:
        raise ObjectiveAcceptanceError("CANDIDATE_UNKNOWN_FIELDS:" + ",".join(extra))

    response = candidate.get("response_text")
    if response is not None and not isinstance(response, str):
        raise ObjectiveAcceptanceError("CANDIDATE_RESPONSE_TEXT_INVALID")

    fields = candidate.get("fields")
    if fields is not None and not isinstance(fields, Mapping):
        raise ObjectiveAcceptanceError("CANDIDATE_FIELDS_INVALID")

    evidence = candidate.get("evidence")
    if evidence is not None and not isinstance(evidence, Mapping):
        raise ObjectiveAcceptanceError("CANDIDATE_EVIDENCE_INVALID")

    return {
        "response_text": response,
        "fields": dict(fields or {}),
        "evidence": dict(evidence or {}),
    }


def _formal_route(text: str, response_text: str | None) -> dict[str, Any]:
    if response_text is None:
        return {
            "route_id": "INSTRUCTION_CONSTRAINTS_V1",
            "status": "UNRESOLVED__CANDIDATE_RESPONSE_TEXT_MISSING",
            "pass": False,
        }
    try:
        constraints = compile_constraints(text)
    except ConstraintError as exc:
        return {
            "route_id": "INSTRUCTION_CONSTRAINTS_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": str(exc),
        }
    ok, errors = validate_response(response_text, constraints)
    return {
        "route_id": "INSTRUCTION_CONSTRAINTS_V1",
        "status": (
            "PASS__FORMAL_RESPONSE_CONSTRAINTS"
            if ok
            else "FALSIFIED__FORMAL_RESPONSE_CONSTRAINTS"
        ),
        "pass": ok,
        "validation_errors": list(errors),
    }


def _typed_route(program: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    verdict = verify_typed_program(
        program,
        trusted_values={},
        candidate_values=dict(fields),
    )
    return {
        "route_id": "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
        "status": str(verdict.get("status") or "FAIL_CLOSED"),
        "pass": verdict.get("pass") is True,
        "verdict": verdict,
    }


def compile_model(
    task_text: str,
    *,
    source_id: str = "user",
    routing_target_effects: Sequence[str] = ("candidate.ready",),
    candidate_field_schema: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    contract = compile_contract(
        task_text,
        source_id=source_id,
        routing_target_effects=list(routing_target_effects),
    )
    if contract.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED__RAW_TASK_CONTRACT",
            "pass": False,
            "contract": contract,
            "terminal_authority": False,
        }

    localized = localize(
        contract,
        candidate_field_schema=candidate_field_schema,
    )
    if localized.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED__ACCEPTANCE_RESIDUAL_LOCALIZATION",
            "pass": False,
            "contract": contract,
            "localization": localized,
            "terminal_authority": False,
        }

    complete = localized.get("semantic_residual_obligation_count") == 0
    model_payload = {
        "task_contract_sha256": contract.get("task_contract_sha256"),
        "objective_route_obligation_ids": localized.get(
            "objective_route_obligation_ids"
        ),
        "semantic_residual_obligation_ids": localized.get(
            "semantic_residual_obligation_ids"
        ),
        "candidate_field_schema": dict(candidate_field_schema or {}),
    }
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": (
            "COMPILED__OBJECTIVE_ACCEPTANCE_MODEL_COMPLETE"
            if complete
            else "COMPILED__OBJECTIVE_ACCEPTANCE_MODEL_WITH_SEMANTIC_RESIDUALS"
        ),
        "pass": True,
        "objective_acceptance_model_complete": complete,
        "task_contract": contract,
        "localization": localized,
        "model_sha256": _sha(model_payload),
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "benchmark_identifier_used_for_routing": False,
        "terminal_authority": False,
    }


def evaluate_candidate(
    task_text: str,
    candidate: Mapping[str, Any],
    *,
    source_id: str = "user",
    routing_target_effects: Sequence[str] = ("candidate.ready",),
    candidate_field_schema: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    try:
        cand = _candidate(candidate)
        model = compile_model(
            task_text,
            source_id=source_id,
            routing_target_effects=routing_target_effects,
            candidate_field_schema=candidate_field_schema,
        )
        if model.get("pass") is not True:
            return {
                **model,
                "candidate_accepted": False,
                "acceptance_stop_authorized": False,
            }

        contract = model["task_contract"]
        localization = model["localization"]
        candidate_sha = _sha(cand)

        if localization.get("semantic_residual_obligation_count") != 0:
            return {
                "schema": SCHEMA,
                "capability_id": CAPABILITY_ID,
                "status": "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS",
                "pass": False,
                "candidate_accepted": False,
                "acceptance_stop_authorized": False,
                "candidate_sha256": candidate_sha,
                "model_sha256": model["model_sha256"],
                "task_contract_sha256": contract.get("task_contract_sha256"),
                "semantic_residual_obligation_ids": list(
                    localization.get("semantic_residual_obligation_ids") or []
                ),
                "objective_route_obligation_ids": list(
                    localization.get("objective_route_obligation_ids") or []
                ),
                "all_raw_obligations_accounted_for": localization.get(
                    "all_required_obligations_accounted_for"
                ) is True,
                "existing_test_success_is_complete_acceptance": False,
                "terminal_authority": False,
                "hard_nonclaim": (
                    "UNBOUND_RAW_TASK_SEMANTICS_REMAIN__NO_ACCEPTANCE_CREDIT"
                ),
            }

        obligation_by_id = {
            row["obligation_id"]: row
            for row in contract["acceptance_contract"]["obligations"]
        }
        results = []
        any_failed = False
        for localized_row in localization["obligations"]:
            oid = localized_row["obligation_id"]
            source_text = obligation_by_id[oid]["text"]
            route_results = []
            for route in localized_row.get("available_objective_routes") or []:
                route_id = route.get("route_id")
                if route_id == "INSTRUCTION_CONSTRAINTS_V1":
                    rr = _formal_route(source_text, cand["response_text"])
                elif route_id == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":
                    program = route.get("acceptance_program")
                    if not isinstance(program, Mapping):
                        rr = {
                            "route_id": str(route_id),
                            "status": "FAIL_CLOSED__ACCEPTANCE_PROGRAM_MISSING",
                            "pass": False,
                        }
                    else:
                        rr = _typed_route(program, cand["fields"])
                else:
                    rr = {
                        "route_id": str(route_id),
                        "status": "FAIL_CLOSED__UNKNOWN_OBJECTIVE_ROUTE",
                        "pass": False,
                    }
                route_results.append(rr)

            obligation_pass = bool(route_results) and all(
                row.get("pass") is True for row in route_results
            )
            if not obligation_pass:
                any_failed = True
            results.append(
                {
                    "obligation_id": oid,
                    "segment_sha256": obligation_by_id[oid]["segment_sha256"],
                    "pass": obligation_pass,
                    "route_results": route_results,
                }
            )

        accepted = (
            not any_failed
            and len(results) == localization.get("required_obligation_count")
        )
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": (
                "PASS__EVERY_OBJECTIVELY_BOUND_RAW_TASK_OBLIGATION_ACCEPTED"
                if accepted
                else "FALSIFIED__OBJECTIVE_ACCEPTANCE_MODEL"
            ),
            "pass": accepted,
            "candidate_accepted": accepted,
            "acceptance_stop_authorized": accepted,
            "candidate_sha256": candidate_sha,
            "model_sha256": model["model_sha256"],
            "task_contract_sha256": contract.get("task_contract_sha256"),
            "required_obligation_count": localization.get(
                "required_obligation_count"
            ),
            "evaluated_obligation_count": len(results),
            "obligation_results": results,
            "semantic_residual_obligation_ids": [],
            "all_raw_obligations_accounted_for": True,
            "existing_test_success_is_complete_acceptance": False,
            "model_dependency_count": 0,
            "external_general_purpose_model_runtime_dependency_count": 0,
            "benchmark_identifier_used_for_routing": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "hard_nonclaims": [
                "ONLY_THE_CURRENTLY_OBJECTIVE_BOUND_RAW_TASK_SUBSET_IS_EXECUTABLE",
                "DIRECT_CANDIDATE_FIELDS_ARE_NOT_CONTENT_ADDRESSED_ARTIFACT_MEASUREMENTS",
                "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
                "NO_BENCHMARK_SCORE_OR_TERMINAL_CREDIT",
            ],
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "candidate_accepted": False,
            "acceptance_stop_authorized": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
