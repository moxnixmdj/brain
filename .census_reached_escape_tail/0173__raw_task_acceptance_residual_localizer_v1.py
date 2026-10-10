"""Fail-closed localizer for lossless raw-task acceptance residuals.

This module does not judge task meaning and does not mint acceptance receipts.

It takes a PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1 and determines, for every
preserved raw-source obligation, whether at least one existing deterministic
acceptance compiler can produce a machine-checkable verifier program from that
exact source segment.

Supported objective route discovery:
- INSTRUCTION_CONSTRAINTS_V1 for explicit textual response-form constraints.
- SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1 when an explicit candidate field schema is
  supplied and the entire normative segment is accepted by that controlled grammar.

Recognizing an imperative/modal head is evidence about requirement *identity*, not
proof of candidate acceptance. Such rows remain semantic residuals unless an
objective acceptance route is independently available.

The output accounts for every required raw obligation exactly once and exposes the
remaining semantic residual set. It grants zero acceptance, capability, or terminal
credit.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.instruction_constraint_compiler_v1 import (
    ConstraintError,
    compile_constraints,
)
from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program

SCHEMA = "PROJECT_BRAIN_RAW_TASK_ACCEPTANCE_RESIDUAL_LOCALIZER_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1"


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "objective_route_obligation_count": 0,
        "semantic_residual_obligation_count": 0,
        "acceptance_credit_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def _formal_signal(constraints: Any) -> bool:
    row = asdict(constraints)
    for key, value in row.items():
        if key in {"required_literals", "forbidden_literals"}:
            if value:
                return True
        elif isinstance(value, bool):
            if value:
                return True
        elif value is not None:
            return True
    return False


def _validate_contract(task_contract: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[str]]:
    if not isinstance(task_contract, Mapping):
        raise ValueError("TASK_CONTRACT_NOT_OBJECT")
    if task_contract.get("schema") != CONTRACT_SCHEMA:
        raise ValueError("TASK_CONTRACT_SCHEMA_INVALID")
    if task_contract.get("pass") is not True:
        raise ValueError("TASK_CONTRACT_NOT_PASS")
    if task_contract.get("status") != "COMPILED__LOSSLESS_RAW_TASK_ACCEPTANCE_CONTRACT":
        raise ValueError("TASK_CONTRACT_STATUS_INVALID")

    acceptance = task_contract.get("acceptance_contract")
    if not isinstance(acceptance, Mapping):
        raise ValueError("ACCEPTANCE_CONTRACT_MISSING")
    if acceptance.get("raw_source_is_final_semantic_reference") is not True:
        raise ValueError("RAW_SOURCE_NOT_FINAL_SEMANTIC_REFERENCE")
    if acceptance.get("unverified_obligation_may_be_silently_dropped") is not False:
        raise ValueError("SILENT_OBLIGATION_DROP_NOT_FORBIDDEN")

    rows = acceptance.get("obligations")
    required = acceptance.get("required_obligation_ids")
    if not isinstance(rows, list) or not rows:
        raise ValueError("ACCEPTANCE_OBLIGATIONS_INVALID")
    if not isinstance(required, list) or not required:
        raise ValueError("REQUIRED_OBLIGATION_IDS_INVALID")
    if any(not isinstance(x, str) or not x for x in required):
        raise ValueError("REQUIRED_OBLIGATION_ID_INVALID")
    if len(required) != len(set(required)):
        raise ValueError("REQUIRED_OBLIGATION_ID_DUPLICATE")

    by_id: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("ACCEPTANCE_OBLIGATION_NOT_OBJECT:" + str(index))
        oid = row.get("obligation_id")
        text = row.get("text")
        segment_sha = row.get("segment_sha256")
        if not isinstance(oid, str) or not oid or oid in by_id:
            raise ValueError("OBLIGATION_ID_INVALID_OR_DUPLICATE:" + str(index))
        if row.get("kind") != "RAW_SOURCE_SEGMENT_ACCEPTANCE":
            raise ValueError("OBLIGATION_KIND_INVALID:" + oid)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("OBLIGATION_TEXT_INVALID:" + oid)
        if not isinstance(segment_sha, str) or len(segment_sha) != 64:
            raise ValueError("SEGMENT_SHA256_INVALID:" + oid)
        if sha256(text.encode("utf-8")).hexdigest() != segment_sha:
            raise ValueError("SEGMENT_SHA256_MISMATCH:" + oid)
        if row.get("acceptance_receipt_required") is not True:
            raise ValueError("ACCEPTANCE_RECEIPT_REQUIREMENT_DISABLED:" + oid)
        by_id[oid] = row

    if set(required) != set(by_id):
        raise ValueError("REQUIRED_OBLIGATION_SET_MISMATCH")
    return [by_id[oid] for oid in required], list(required)


def _structured_ids(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("structured_requirement_ids")
    if not isinstance(raw, list):
        return []
    return sorted({x for x in raw if isinstance(x, str) and x})


def localize(
    task_contract: Mapping[str, Any],
    *,
    candidate_field_schema: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Partition every raw obligation into objective-route-available or semantic residual.

    Route availability is deliberately weaker than acceptance. The downstream
    verifier must still execute against the exact candidate, and the lossless
    acceptance gate must still receive independently verified content-addressed
    acceptance receipts for every obligation.
    """
    try:
        rows, required_ids = _validate_contract(task_contract)
        if candidate_field_schema is not None and not isinstance(candidate_field_schema, Mapping):
            raise ValueError("CANDIDATE_FIELD_SCHEMA_INVALID")

        localized: list[dict[str, Any]] = []
        objective_ids: list[str] = []
        residual_ids: list[str] = []

        for row in rows:
            oid = str(row["obligation_id"])
            text = str(row["text"])
            routes: list[dict[str, Any]] = []
            diagnostics: list[dict[str, Any]] = []

            try:
                constraints = compile_constraints(text)
                if _formal_signal(constraints):
                    routes.append({
                        "route_id": "INSTRUCTION_CONSTRAINTS_V1",
                        "kind": "FORMAL",
                        "compiler": "canonical/runtime/instruction_constraint_compiler_v1.py",
                        "compiled_constraints": asdict(constraints),
                        "scope_claim": "EXPLICIT_TEXTUAL_RESPONSE_FORM_CONSTRAINTS_ONLY",
                    })
                else:
                    diagnostics.append({
                        "route_id": "INSTRUCTION_CONSTRAINTS_V1",
                        "status": "NO_FORMAL_CONSTRAINT_SIGNAL",
                    })
            except ConstraintError as exc:
                diagnostics.append({
                    "route_id": "INSTRUCTION_CONSTRAINTS_V1",
                    "status": "FAIL_CLOSED",
                    "reason": str(exc),
                })

            if candidate_field_schema is not None:
                compiled = compile_program(
                    text,
                    source_id=oid,
                    field_schema=candidate_field_schema,
                )
                if compiled.get("status") == "COMPILED":
                    routes.append({
                        "route_id": "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
                        "kind": "DETERMINISTIC",
                        "compiler": "canonical/runtime/source_aligned_acceptance_program_v1.py",
                        "acceptance_program": compiled.get("acceptance_program"),
                        "compiled_requirements": compiled.get("compiled_requirements", []),
                        "scope_claim": "CONTROLLED_EXACT_FIELD_MUST_CONSTRAINT_GRAMMAR_ONLY",
                    })
                else:
                    diagnostics.append({
                        "route_id": "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
                        "status": str(compiled.get("status") or "UNKNOWN"),
                        "reason": compiled.get("reason"),
                        "unresolved_normative_requirements": compiled.get(
                            "unresolved_normative_requirements", []
                        ),
                    })

            structured = _structured_ids(row)
            if routes:
                status = "OBJECTIVE_ACCEPTANCE_ROUTE_AVAILABLE"
                objective_ids.append(oid)
                residual_reason = None
            else:
                status = "SEMANTIC_ADJUDICATION_REQUIRED"
                residual_ids.append(oid)
                residual_reason = (
                    "SOURCE_BOUND_REQUIREMENT_IDENTIFIED_BUT_NO_SOUND_CANDIDATE_ACCEPTANCE_SEMANTICS_COMPILED"
                    if structured
                    else "NO_SOUND_OBJECTIVE_CANDIDATE_ACCEPTANCE_ROUTE_FOR_RAW_SEGMENT"
                )

            localized.append({
                "obligation_id": oid,
                "segment_index": row.get("segment_index"),
                "segment_sha256": row.get("segment_sha256"),
                "status": status,
                "available_objective_routes": routes,
                "route_diagnostics": diagnostics,
                "structured_requirement_ids": structured,
                "semantic_residual_reason": residual_reason,
                "acceptance_receipt_still_required": True,
                "accepted": False,
            })

        if len(localized) != len(required_ids):
            raise ValueError("LOCALIZATION_CARDINALITY_MISMATCH")
        if set(objective_ids) & set(residual_ids):
            raise ValueError("LOCALIZATION_PARTITION_OVERLAP")
        if set(objective_ids) | set(residual_ids) != set(required_ids):
            raise ValueError("LOCALIZATION_PARTITION_INCOMPLETE")

        return {
            "schema": SCHEMA,
            "status": "PASS__LOSSLESS_RAW_TASK_ACCEPTANCE_RESIDUAL_LOCALIZED",
            "pass": True,
            "task_contract_sha256": task_contract.get("task_contract_sha256"),
            "required_obligation_count": len(required_ids),
            "accounted_obligation_count": len(localized),
            "all_required_obligations_accounted_for": True,
            "objective_route_obligation_count": len(objective_ids),
            "semantic_residual_obligation_count": len(residual_ids),
            "objective_route_obligation_ids": objective_ids,
            "semantic_residual_obligation_ids": residual_ids,
            "obligations": localized,
            "objective_route_availability_is_acceptance": False,
            "semantic_parser_recognition_is_acceptance": False,
            "missing_route_may_be_silently_ignored": False,
            "acceptance_credit_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "next": (
                "EXECUTE_AVAILABLE_OBJECTIVE_VERIFIERS_AGAINST_THE_EXACT_CANDIDATE;"
                "FOR_ONLY_THE_SEMANTIC_RESIDUAL_IDS_OBTAIN_AUTHENTICATED_CONFIGURED_DOMAIN_OR_OTHER_SOUND_ACCEPTANCE;"
                "THEN_FEED_ALL_INDEPENDENTLY_VERIFIED_RECEIPTS_TO_RAW_TASK_ACCEPTANCE_V1"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
