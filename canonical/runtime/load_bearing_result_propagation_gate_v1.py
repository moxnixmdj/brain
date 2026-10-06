from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from canonical.runtime import honesty_envelope_v1 as honesty

CERT_SCHEMA = "PROJECT_BRAIN_LOAD_BEARING_RESULT_CERTIFICATE_V1"
PASS_STATUS = "PASS__CONTENT_BOUND_HONESTY_CERTIFIED_LOAD_BEARING_RESULT"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LoadBearingResultError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LoadBearingResultError("RESULT_NOT_CANONICAL_JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LoadBearingResultError(name + "_INVALID")
    return value.strip()


def _sha64(value: Any, name: str) -> str:
    out = _token(value, name).lower()
    if not HEX64.fullmatch(out):
        raise LoadBearingResultError(name + "_INVALID")
    return out


def _step_binding(
    *,
    result: Any,
    mission_id: str,
    mission_sha256: str,
    step_index: int,
    step_id: str,
    verification_ok: bool,
) -> dict[str, Any]:
    if not isinstance(step_index, int) or isinstance(step_index, bool) or step_index < 0:
        raise LoadBearingResultError("STEP_INDEX_INVALID")
    if not isinstance(verification_ok, bool):
        raise LoadBearingResultError("VERIFICATION_OK_INVALID")
    return {
        "mission_id": _token(mission_id, "MISSION_ID"),
        "mission_sha256": _sha64(mission_sha256, "MISSION_SHA256"),
        "step_index": step_index,
        "step_id": _token(step_id, "STEP_ID"),
        "result_sha256": _sha(result),
        "verification_ok": verification_ok,
    }


def _honesty_record(binding: Mapping[str, Any]) -> dict[str, Any]:
    ok = binding["verification_ok"] is True
    receipt = binding["result_sha256"]
    return {
        "schema": "PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
        "task_contract": {
            "task_id": (
                str(binding["mission_id"])
                + ":"
                + str(binding["step_index"])
                + ":"
                + str(binding["step_id"])
            ),
            "required_obligations": ["STEP_RESULT_VERIFICATION"],
        },
        "obligations": [
            {
                "id": "STEP_RESULT_VERIFICATION",
                "state": "VERIFIED" if ok else "FAILED",
                "receipts": [receipt] if ok else [],
            }
        ],
        "completion_claim": "COMPLETE" if ok else "FAILED",
        "provenance_events": [],
        "material_claims": [],
        "belief_assertions": [],
        "load_bearing_result_binding": dict(binding),
        "ledger_semantic_completeness_claimed": False,
    }


def certify_result(
    result: Any,
    *,
    mission_id: str,
    mission_sha256: str,
    step_index: int,
    step_id: str,
    verification_ok: bool,
) -> dict[str, Any]:
    binding = _step_binding(
        result=result,
        mission_id=mission_id,
        mission_sha256=mission_sha256,
        step_index=step_index,
        step_id=step_id,
        verification_ok=verification_ok,
    )
    record = _honesty_record(binding)
    verdict = honesty.adjudicate(record)
    if verdict.get("status") != "PASS":
        raise LoadBearingResultError("HONESTY_ENVELOPE_DENIED")
    cert = {
        "schema": CERT_SCHEMA,
        "status": PASS_STATUS,
        "binding": binding,
        "binding_sha256": _sha(binding),
        "honesty_record": record,
        "honesty_record_sha256": _sha(record),
        "honesty_result": verdict,
        "honesty_result_sha256": _sha(verdict),
        "ledger_semantic_completeness_claimed": False,
        "scope": "LOAD_BEARING_STEP_RESULT_PROPAGATION_ONLY",
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    return cert


def verify_certificate(
    result: Any,
    certificate: Mapping[str, Any],
    *,
    mission_id: str,
    mission_sha256: str,
    step_index: int,
    step_id: str,
    verification_ok: bool,
) -> dict[str, Any]:
    try:
        if not isinstance(certificate, Mapping):
            raise LoadBearingResultError("CERTIFICATE_MAPPING_REQUIRED")
        if certificate.get("schema") != CERT_SCHEMA:
            raise LoadBearingResultError("CERTIFICATE_SCHEMA_INVALID")
        if certificate.get("status") != PASS_STATUS:
            raise LoadBearingResultError("CERTIFICATE_STATUS_INVALID")

        expected = _step_binding(
            result=result,
            mission_id=mission_id,
            mission_sha256=mission_sha256,
            step_index=step_index,
            step_id=step_id,
            verification_ok=verification_ok,
        )
        binding = certificate.get("binding")
        if not isinstance(binding, Mapping) or dict(binding) != expected:
            raise LoadBearingResultError("RESULT_BINDING_MISMATCH")
        if certificate.get("binding_sha256") != _sha(expected):
            raise LoadBearingResultError("BINDING_HASH_MISMATCH")

        record = certificate.get("honesty_record")
        if not isinstance(record, Mapping):
            raise LoadBearingResultError("HONESTY_RECORD_MISSING")
        if certificate.get("honesty_record_sha256") != _sha(record):
            raise LoadBearingResultError("HONESTY_RECORD_HASH_MISMATCH")
        if record.get("load_bearing_result_binding") != expected:
            raise LoadBearingResultError("HONESTY_RECORD_RESULT_BINDING_MISMATCH")
        if record.get("ledger_semantic_completeness_claimed") is not False:
            raise LoadBearingResultError("LEDGER_COMPLETENESS_OVERCLAIM")

        verdict = honesty.adjudicate(record)
        if verdict.get("status") != "PASS":
            raise LoadBearingResultError("HONESTY_ENVELOPE_DENIED")
        if certificate.get("honesty_result") != verdict:
            raise LoadBearingResultError("HONESTY_RESULT_MISMATCH")
        if certificate.get("honesty_result_sha256") != _sha(verdict):
            raise LoadBearingResultError("HONESTY_RESULT_HASH_MISMATCH")

        return {
            "schema": "PROJECT_BRAIN_LOAD_BEARING_RESULT_CERTIFICATE_VERIFICATION_V1",
            "status": "PASS",
            "result_sha256": expected["result_sha256"],
            "binding_sha256": certificate["binding_sha256"],
            "honesty_result_sha256": certificate["honesty_result_sha256"],
            "ledger_semantic_completeness_claimed": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_LOAD_BEARING_RESULT_CERTIFICATE_VERIFICATION_V1",
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
