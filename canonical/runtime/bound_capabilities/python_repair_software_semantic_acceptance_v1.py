"""Python repair V9: bounded software-request semantic acceptance.

V9 preserves the verified V8 repair -> realization -> content-addressed measurement
path. When V8 is blocked only by raw-task semantic residuals, V9 may discharge
only explicit software postconditions recognized by the bounded one-sided
software-request acceptance cells.

The cells consume measurement fields produced internally by the same V8 call.
Caller-supplied measurements never authorize acceptance here.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import (
    python_repair_measured_acceptance_controller_v1 as v8,
)
from canonical.runtime import python_software_request_acceptance_cells_v1 as cells

SCHEMA = "PROJECT_BRAIN_PYTHON_REPAIR_SOFTWARE_SEMANTIC_ACCEPTANCE_V1"
CAPABILITY_ID = "python.software.repair.semantic_acceptance.v1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0


class RepairSemanticAcceptanceError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_output(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p == repo or repo not in p.parents:
        raise RepairSemanticAcceptanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise RepairSemanticAcceptanceError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    task_text = str(args.get("task_text") or "").strip()
    if not task_text:
        raise RepairSemanticAcceptanceError("TASK_TEXT_REQUIRED")
    output = _safe_output(repo, args.get("output_path"))

    v8_output = output.parent / (".v9_v8_" + output.name)
    v8_args = dict(args)
    v8_args["output_path"] = _rel(repo, v8_output)
    try:
        base = v8.run(v8_args, repo)
    finally:
        if v8_output.exists():
            v8_output.unlink()

    if base.get("pass") is True and base.get("acceptance_stop_authorized") is True:
        result = {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "PASS__V8_MEASUREMENT_BOUND_OBJECTIVE_ACCEPTANCE",
            "pass": True,
            "repair_pass": True,
            "acceptance_stop_authorized": True,
            "acceptance_route": "V8_EXISTING_OBJECTIVE_ACCEPTANCE",
            "v8_status": base.get("status"),
            "candidate_subject_snapshot_sha256": base.get("candidate_subject_snapshot_sha256"),
            "measurement_receipt_payload_sha256": base.get("measurement_receipt_payload_sha256"),
            "measurement_program_sha256": base.get("measurement_program_sha256"),
            "measurement_spec_sha256": base.get("measurement_spec_sha256"),
            "source_restored": base.get("source_restored") is True,
            "model_dependency_count": 0,
            "external_general_purpose_model_runtime_dependency_count": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }
    elif base.get("repair_pass") is True:
        measured = base.get("measured_fields")
        required_hashes = {
            "candidate_subject_snapshot_sha256": base.get("candidate_subject_snapshot_sha256"),
            "measurement_receipt_payload_sha256": base.get("measurement_receipt_payload_sha256"),
            "measurement_program_sha256": base.get("measurement_program_sha256"),
            "measurement_spec_sha256": base.get("measurement_spec_sha256"),
        }
        if not isinstance(measured, Mapping):
            raise RepairSemanticAcceptanceError("V8_MEASURED_FIELDS_MISSING")
        if any(not isinstance(v, str) or len(v) != 64 for v in required_hashes.values()):
            raise RepairSemanticAcceptanceError("V8_MEASUREMENT_BINDING_HASH_MISSING")

        semantic = cells.evaluate_task(
            task_text,
            measured,
            response_text=(
                str(args["response_text"]) if args.get("response_text") is not None else None
            ),
        )
        accepted = (
            semantic.get("pass") is True
            and semantic.get("all_raw_obligations_accounted_for") is True
            and not semantic.get("semantic_residual_obligation_ids")
            and base.get("source_restored") is True
        )
        result = {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": (
                "PASS__REPAIR_MEASURED_AND_BOUNDED_SOFTWARE_SEMANTIC_ACCEPTANCE"
                if accepted
                else "OPEN__REPAIR_FOUND_BUT_SOFTWARE_SEMANTIC_ACCEPTANCE_INCOMPLETE"
            ),
            "pass": accepted,
            "repair_pass": True,
            "acceptance_stop_authorized": accepted,
            "acceptance_route": "BOUNDED_SOFTWARE_REQUEST_CELLS_V1",
            "v8_status": base.get("status"),
            "v8_acceptance_status": base.get("acceptance_status"),
            "software_semantic_result": semantic,
            "measured_fields": dict(measured),
            **required_hashes,
            "source_restored": base.get("source_restored") is True,
            "measurement_fields_origin": "INTERNAL_SAME_CALL_V8_CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT",
            "model_dependency_count": 0,
            "external_general_purpose_model_runtime_dependency_count": 0,
            "incremental_spend_usd": 0,
            "hard_nonclaims": [
                "ONLY_BOUNDED_EXPLICIT_SOFTWARE_POSTCONDITION_CELLS_GAIN_NEW_SEMANTIC_COVERAGE",
                "VAGUE_TASK_SPECIFIC_REPAIR_LANGUAGE_REMAINS_BLOCKING",
                "NO_ARBITRARY_PATCH_SEARCH_COMPLETENESS",
                "NO_NON_PYTHON_SUPPORT",
                "NO_TEST_PASS_EQUALS_GENERAL_MERGEABILITY",
                "NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY",
            ],
            "terminal_authority": False,
        }
    else:
        result = {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH",
            "pass": False,
            "repair_pass": False,
            "acceptance_stop_authorized": False,
            "v8_status": base.get("status"),
            "source_restored": base.get("source_restored") is True,
            "model_dependency_count": 0,
            "external_general_purpose_model_runtime_dependency_count": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = output.read_bytes()
    return {
        **result,
        "output_path": _rel(repo, output),
        "output_sha256": _sha(raw),
        "output_verified": True,
    }
