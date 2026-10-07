from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.content_addressed_artifact_measurement_v1 import measure
from canonical.runtime.typed_acceptance_program_v1 import verify as verify_program

SCHEMA = "PROJECT_BRAIN_MEASURED_TYPED_ACCEPTANCE_PROGRAM_V1"


def _candidate_field_types(program: Mapping[str, Any]) -> dict[str, str]:
    rows = program.get("fields")
    if not isinstance(rows, list):
        raise ValueError("PROGRAM_FIELDS_REQUIRED")
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("PROGRAM_FIELD_INVALID")
        if row.get("source") != "candidate":
            continue
        fid = row.get("id")
        typ = row.get("type")
        if not isinstance(fid, str) or not fid or not isinstance(typ, str) or not typ:
            raise ValueError("PROGRAM_CANDIDATE_FIELD_INVALID")
        if fid in out:
            raise ValueError("PROGRAM_CANDIDATE_FIELD_DUPLICATE:" + fid)
        out[fid] = typ
    return out


def verify(
    program: Mapping[str, Any],
    *,
    artifact_path: str,
    measurements: Sequence[Mapping[str, Any]],
    trusted_values: Mapping[str, Any],
    root: str,
    expected_artifact_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(program, Mapping):
            raise ValueError("PROGRAM_NOT_OBJECT")
        if not isinstance(trusted_values, Mapping):
            raise ValueError("TRUSTED_VALUES_NOT_OBJECT")

        receipt = measure(artifact_path, measurements, root=root)
        if receipt.get("status") != "MEASURED":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "ARTIFACT_MEASUREMENT_FAILED",
                "measurement_receipt": receipt,
                "terminal_authority": False,
            }

        artifact_sha = receipt["artifact_sha256"]
        if expected_artifact_sha256 is not None:
            if (
                not isinstance(expected_artifact_sha256, str)
                or len(expected_artifact_sha256) != 64
                or expected_artifact_sha256 != artifact_sha
            ):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "pass": False,
                    "reason": "ARTIFACT_SHA256_MISMATCH",
                    "artifact_sha256": artifact_sha,
                    "terminal_authority": False,
                }

        expected_types = _candidate_field_types(program)
        measured_types = receipt.get("types") or {}
        if set(expected_types) != set(measured_types):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "PROGRAM_MEASUREMENT_FIELD_SET_MISMATCH",
                "missing_measurements": sorted(set(expected_types) - set(measured_types)),
                "extra_measurements": sorted(set(measured_types) - set(expected_types)),
                "terminal_authority": False,
            }
        mismatches = {
            fid: {"program_type": expected_types[fid], "measurement_type": measured_types[fid]}
            for fid in expected_types
            if expected_types[fid] != measured_types[fid]
        }
        if mismatches:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "PROGRAM_MEASUREMENT_TYPE_MISMATCH",
                "mismatches": mismatches,
                "terminal_authority": False,
            }

        verdict = verify_program(
            program,
            trusted_values=trusted_values,
            candidate_values=receipt["values"],
        )
        passed = verdict.get("pass") is True
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__MEASURED_TYPED_ACCEPTANCE"
                if passed
                else (
                    "FALSIFIED__MEASURED_TYPED_ACCEPTANCE"
                    if str(verdict.get("status") or "").startswith("FALSIFIED")
                    else "FAIL_CLOSED"
                )
            ),
            "pass": passed,
            "artifact_path": receipt["artifact_path"],
            "artifact_sha256": artifact_sha,
            "measurement_receipt_sha256": receipt["receipt_sha256"],
            "measurement_receipt": receipt,
            "acceptance_verdict": verdict,
            "proposal_supplied_candidate_values": False,
            "terminal_authority": False,
            "soundness_boundary": (
                "CANDIDATE_FIELD_VALUES_ARE_DERIVED_FROM_CONTENT_ADDRESSED_ARTIFACT_BYTES;"
                "UPSTREAM_MUST_STILL_PROVE_THE_ARTIFACT_PATH_AND_EACH_MEASUREMENT_FIELD_MEANING"
                "_MATCH_THE_LOAD_BEARING_TASK_CONTRACT"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
