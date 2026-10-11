"""Bounded source-grounded software-request acceptance cells V1.

This module expands objective raw-task acceptance only for explicit software
postconditions that are exactly represented by the existing content-addressed
Python repository measurement schema.

It deliberately does not infer task-specific intent from vague repair language.
Unsupported or ambiguous language remains a blocking semantic residual.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import raw_task_objective_acceptance_executor_v1 as objective
from canonical.runtime.typed_acceptance_program_v1 import PROGRAM_SCHEMA, verify
from canonical.runtime.bound_capabilities.python_repository_acceptance_measurement_v1 import (
    MEASUREMENT_SCHEMA,
)

SCHEMA = "PROJECT_BRAIN_PYTHON_SOFTWARE_REQUEST_ACCEPTANCE_CELLS_V1"
CAPABILITY_ID = "python.task.acceptance.software_request_cells.v1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0

_TERMINAL_PUNCT = re.compile(r"[.!?]+$")
_TESTS_PASS = (
    re.compile(r"^(?:make|ensure)(?: that)? (?:all|the) tests pass$", re.I),
    re.compile(r"^make sure (?:all|the) tests pass$", re.I),
    re.compile(r"^(?:all|the) tests must pass$", re.I),
)
_PARSE_OK = (
    re.compile(r"^(?:ensure|make sure)(?: that)? (?:the )?python (?:code|files?) (?:parses?|can be parsed)$", re.I),
    re.compile(r"^(?:the )?python (?:code|files?) must parse$", re.I),
)
_SOURCE_UNCHANGED = (
    re.compile(r"^(?:keep|ensure)(?: that)? (?:the )?(?:repository )?source(?: tree)? (?:is |remains? )?unchanged during (?:verification|measurement)$", re.I),
    re.compile(r"^(?:the )?(?:repository )?source(?: tree)? must remain unchanged during (?:verification|measurement)$", re.I),
)


def _norm(text: str) -> str:
    value = " ".join(str(text or "").strip().split())
    value = _TERMINAL_PUNCT.sub("", value).strip()
    return value


def _program(field: str) -> dict[str, Any]:
    meta = MEASUREMENT_SCHEMA[field]
    if meta["type"] != "boolean" or meta["dimension"] != "dimensionless":
        raise ValueError("SOFTWARE_CELL_FIELD_NOT_BOOLEAN:" + field)
    return {
        "schema": PROGRAM_SCHEMA,
        "fields": [
            {
                "id": field,
                "type": "boolean",
                "dimension": "dimensionless",
                "source": "candidate",
            }
        ],
        "accept_when": {
            "op": "eq",
            "left": {"op": "ref", "id": field},
            "right": {
                "op": "const",
                "type": "boolean",
                "dimension": "dimensionless",
                "value": True,
            },
        },
    }


def compile_cell(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "SOURCE_SEGMENT_REQUIRED",
            "acceptance_authority": False,
        }
    norm = _norm(text)
    field = None
    cell_id = None
    for regex in _TESTS_PASS:
        if regex.fullmatch(norm):
            field, cell_id = "tests_pass", "EXPLICIT_TESTS_PASS_TRUE"
            break
    if field is None:
        for regex in _PARSE_OK:
            if regex.fullmatch(norm):
                field, cell_id = "python_parse_ok", "EXPLICIT_PYTHON_PARSE_TRUE"
                break
    if field is None:
        for regex in _SOURCE_UNCHANGED:
            if regex.fullmatch(norm):
                field, cell_id = "repository_source_unchanged", "EXPLICIT_SOURCE_UNCHANGED_TRUE"
                break
    if field is None:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED__NO_SOUND_SOFTWARE_ACCEPTANCE_CELL",
            "pass": False,
            "source_segment_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "normalized_text": norm,
            "acceptance_authority": False,
            "hard_nonclaim": "UNSUPPORTED_SOFTWARE_LANGUAGE_REMAINS_A_SEMANTIC_RESIDUAL",
        }
    program = _program(field)
    payload = {
        "cell_id": cell_id,
        "field": field,
        "normalized_text": norm,
        "program": program,
    }
    return {
        "schema": SCHEMA,
        "status": "COMPILED__ONE_SIDED_SOFTWARE_ACCEPTANCE_CELL",
        "pass": True,
        "cell_id": cell_id,
        "field": field,
        "source_segment_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "normalized_text": norm,
        "acceptance_program": program,
        "cell_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "scope": "EXPLICIT_POSTCONDITION_EQUIVALENT_TO_EXISTING_REPOSITORY_MEASUREMENT_ONLY",
        "acceptance_authority": False,
    }


def _cell_verdict(compiled: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    program = compiled.get("acceptance_program")
    if not isinstance(program, Mapping):
        return {"status": "FAIL_CLOSED", "pass": False, "reason": "CELL_PROGRAM_MISSING"}
    verdict = verify(program, trusted_values={}, candidate_values=dict(fields))
    return {
        "status": str(verdict.get("status") or "FAIL_CLOSED"),
        "pass": verdict.get("pass") is True,
        "verdict": verdict,
    }


def evaluate_task(
    task_text: str,
    measured_fields: Mapping[str, Any],
    *,
    response_text: str | None = None,
) -> dict[str, Any]:
    """Evaluate all raw task segments without granting standalone stop authority.

    measured_fields are expected to be supplied internally by a controller that
    just executed the content-addressed repository measurement. This function
    itself does not authenticate an external caller's measurement receipt.
    """
    if not isinstance(measured_fields, Mapping):
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "MEASURED_FIELDS_NOT_OBJECT",
            "acceptance_stop_authorized": False,
        }
    if set(measured_fields) != set(MEASUREMENT_SCHEMA):
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "MEASUREMENT_FIELD_SET_MISMATCH",
            "acceptance_stop_authorized": False,
        }

    contract = compile_contract(
        task_text,
        source_id="software_request",
        routing_target_effects=["candidate.ready"],
    )
    if contract.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED__RAW_TASK_CONTRACT",
            "pass": False,
            "contract": contract,
            "acceptance_stop_authorized": False,
        }

    results = []
    residual_ids = []
    for obligation in contract["acceptance_contract"]["obligations"]:
        oid = obligation["obligation_id"]
        segment = obligation["text"]
        base = objective.evaluate_candidate(
            segment,
            {
                "response_text": response_text,
                "fields": dict(measured_fields),
                "evidence": {},
            },
            source_id="software_request_segment",
            candidate_field_schema=MEASUREMENT_SCHEMA,
        )
        if base.get("acceptance_stop_authorized") is True:
            results.append(
                {
                    "obligation_id": oid,
                    "segment_sha256": obligation["segment_sha256"],
                    "pass": True,
                    "route": "EXISTING_OBJECTIVE_ACCEPTANCE",
                    "route_result": base,
                }
            )
            continue

        if base.get("status") != "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS":
            results.append(
                {
                    "obligation_id": oid,
                    "segment_sha256": obligation["segment_sha256"],
                    "pass": False,
                    "route": "EXISTING_OBJECTIVE_ACCEPTANCE_FALSIFIED_OR_UNRESOLVED",
                    "route_result": base,
                }
            )
            residual_ids.append(oid)
            continue

        cell = compile_cell(segment)
        if cell.get("pass") is not True:
            results.append(
                {
                    "obligation_id": oid,
                    "segment_sha256": obligation["segment_sha256"],
                    "pass": False,
                    "route": "SEMANTIC_RESIDUAL",
                    "cell": cell,
                }
            )
            residual_ids.append(oid)
            continue

        verdict = _cell_verdict(cell, measured_fields)
        ok = verdict.get("pass") is True
        results.append(
            {
                "obligation_id": oid,
                "segment_sha256": obligation["segment_sha256"],
                "pass": ok,
                "route": "SOFTWARE_ACCEPTANCE_CELL_V1",
                "cell_id": cell["cell_id"],
                "field": cell["field"],
                "cell_sha256": cell["cell_sha256"],
                "cell_verdict": verdict,
            }
        )
        if not ok:
            residual_ids.append(oid)

    complete = len(results) == len(contract["acceptance_contract"]["required_obligation_ids"])
    passed = complete and not residual_ids and all(r.get("pass") is True for r in results)
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": (
            "PASS__EVERY_RAW_SEGMENT_OBJECTIVELY_ACCEPTED_WITH_BOUNDED_SOFTWARE_CELLS"
            if passed
            else "OPEN__SOFTWARE_REQUEST_SEMANTIC_RESIDUALS_OR_FALSIFIED_POSTCONDITIONS"
        ),
        "pass": passed,
        "task_contract_sha256": contract.get("task_contract_sha256"),
        "required_obligation_count": len(contract["acceptance_contract"]["required_obligation_ids"]),
        "evaluated_obligation_count": len(results),
        "all_raw_obligations_accounted_for": complete,
        "semantic_residual_obligation_ids": residual_ids,
        "obligation_results": results,
        "measurement_schema_bound": True,
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
        "acceptance_stop_authorized": False,
        "hard_nonclaims": [
            "STANDALONE_CALLER_SUPPLIED_FIELDS_ARE_NOT_AUTHENTICATED_MEASUREMENTS",
            "ONLY_EXPLICIT_POSTCONDITIONS_IN_THE_BOUNDED_CELL_GRAMMAR_GAIN_SEMANTIC_COVERAGE",
            "VAGUE_TASK_SPECIFIC_REPAIR_LANGUAGE_REMAINS_BLOCKING",
            "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_BENCHMARK_SCORE_OR_TERMINAL_AUTHORITY",
        ],
        "terminal_authority": False,
    }
