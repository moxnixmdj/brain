"""Bind raw-task objective acceptance to repository-derived measurements.

Unlike the lower-level V6 executor, this wrapper never accepts caller-supplied
candidate fields. Objective fields come only from a content-addressed measurement
receipt produced by python.repository.acceptance.measure.v1.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

from canonical.runtime import raw_task_objective_acceptance_executor_v1 as objective

SCHEMA = "PROJECT_BRAIN_PYTHON_MEASURED_OBJECTIVE_ACCEPTANCE_V1"
CAPABILITY_ID = "python.task.acceptance.measured.objective.v1"
MEASUREMENT_SCHEMA_ID = "PROJECT_BRAIN_PYTHON_REPOSITORY_ACCEPTANCE_MEASUREMENT_V1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0


class MeasuredAcceptanceError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_obj(value: Any) -> str:
    return _sha_bytes(_canon(value).encode("utf-8"))


def _safe_receipt(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p == repo or repo not in p.parents or not p.is_file() or p.is_symlink():
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_PATH_INVALID")
    return p


def _load_receipt(repo: pathlib.Path, raw: Any) -> tuple[dict[str, Any], str]:
    path = _safe_receipt(repo, raw)
    data = path.read_bytes()
    try:
        receipt = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_JSON_INVALID") from exc
    if not isinstance(receipt, dict):
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_NOT_OBJECT")
    if receipt.get("schema") != MEASUREMENT_SCHEMA_ID:
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_SCHEMA_INVALID")
    if receipt.get("pass") is not True:
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_NOT_PASS")
    claimed = receipt.get("receipt_payload_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_HASH_MISSING")
    payload = dict(receipt)
    payload.pop("receipt_payload_sha256", None)
    if _sha_obj(payload) != claimed:
        raise MeasuredAcceptanceError("MEASUREMENT_RECEIPT_HASH_MISMATCH")
    schema = receipt.get("measurement_schema")
    values = receipt.get("measurements")
    if not isinstance(schema, dict) or not schema:
        raise MeasuredAcceptanceError("MEASUREMENT_FIELD_SCHEMA_INVALID")
    if not isinstance(values, dict) or set(values) != set(schema):
        raise MeasuredAcceptanceError("MEASUREMENT_FIELD_SET_MISMATCH")
    if values.get("repository_source_unchanged") is not True:
        raise MeasuredAcceptanceError("MEASUREMENT_SOURCE_UNCHANGED_NOT_PROVED")
    subject = receipt.get("subject")
    if not isinstance(subject, dict) or not isinstance(subject.get("snapshot_sha256"), str):
        raise MeasuredAcceptanceError("MEASUREMENT_SUBJECT_BINDING_MISSING")
    return receipt, _sha_bytes(data)


def evaluate_from_receipt(
    task_text: str,
    *,
    measurement_receipt_path: str,
    root: str | pathlib.Path,
    response_text: str | None = None,
) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    try:
        receipt, receipt_file_sha = _load_receipt(repo, measurement_receipt_path)
        result = objective.evaluate_candidate(
            task_text,
            {
                "response_text": response_text,
                "fields": dict(receipt["measurements"]),
                "evidence": {
                    "measurement_receipt_file_sha256": receipt_file_sha,
                    "measurement_receipt_payload_sha256": receipt["receipt_payload_sha256"],
                    "subject_snapshot_sha256": receipt["subject"]["snapshot_sha256"],
                    "measurement_program_sha256": receipt["measurement_program_sha256"],
                },
            },
            candidate_field_schema=receipt["measurement_schema"],
        )
        accepted = result.get("acceptance_stop_authorized") is True
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": (
                "PASS__MEASUREMENT_BOUND_OBJECTIVE_ACCEPTANCE"
                if accepted
                else str(result.get("status") or "FAIL_CLOSED")
            ),
            "pass": accepted,
            "candidate_accepted": result.get("candidate_accepted") is True,
            "acceptance_stop_authorized": accepted,
            "measurement_bound": True,
            "measurement_receipt_file_sha256": receipt_file_sha,
            "measurement_receipt_payload_sha256": receipt["receipt_payload_sha256"],
            "subject_snapshot_sha256": receipt["subject"]["snapshot_sha256"],
            "measurement_program_sha256": receipt["measurement_program_sha256"],
            "measurement_spec_sha256": receipt["measurement_spec_sha256"],
            "objective_result": result,
            "model_dependency_count": 0,
            "external_general_purpose_model_runtime_dependency_count": 0,
            "incremental_spend_usd": 0,
            "hard_nonclaims": [
                "ONLY_OBJECTIVELY_COMPILED_RAW_TASK_OBLIGATIONS_CAN_CLEAR",
                "SEMANTIC_RESIDUALS_STILL_BLOCK_ACCEPTANCE",
                "MEASUREMENT_BINDING_DOES_NOT_CREATE_MISSING_TASK_SEMANTICS",
                "NO_GENERAL_SOFTWARE_ENGINEERING_COMPLETENESS",
                "NO_BENCHMARK_SCORE_OR_TERMINAL_AUTHORITY",
            ],
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "candidate_accepted": False,
            "acceptance_stop_authorized": False,
            "measurement_bound": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    if not isinstance(args, dict):
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "acceptance_stop_authorized": False,
            "errors": ["ARGS_NOT_OBJECT"],
            "terminal_authority": False,
        }
    result = evaluate_from_receipt(
        str(args.get("task_text") or ""),
        measurement_receipt_path=str(args.get("measurement_receipt_path") or ""),
        root=root,
        response_text=(
            str(args["response_text"]) if args.get("response_text") is not None else None
        ),
    )
    output_raw = args.get("output_path")
    if not output_raw:
        return result
    repo = pathlib.Path(root).resolve()
    output = (repo / str(output_raw)).resolve()
    if output == repo or repo not in output.parents:
        return {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "status": "FAIL_CLOSED",
            "pass": False,
            "acceptance_stop_authorized": False,
            "errors": ["OUTPUT_PATH_OUTSIDE_REPOSITORY"],
            "terminal_authority": False,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = output.read_bytes()
    return {
        **result,
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": _sha_bytes(raw),
        "output_verified": True,
    }
