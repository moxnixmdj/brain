from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import honesty_envelope_v1 as honesty

CERT_SCHEMA = "PROJECT_BRAIN_LOAD_BEARING_HONESTY_CERTIFICATE_V1"
FINAL_SCHEMA = "PROJECT_BRAIN_TERMINAL_HONESTY_CERTIFICATE_V1"


class LoadBearingHonestyError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LoadBearingHonestyError(name + "_INVALID")
    return value.strip()


def certify_result(
    *,
    mission_id: str,
    mission_sha256: str,
    step_index: int,
    step_id: str,
    result: Mapping[str, Any],
    honesty_record: Mapping[str, Any],
) -> dict[str, Any]:
    mission_id = _token(mission_id, "MISSION_ID")
    mission_sha256 = _token(mission_sha256, "MISSION_SHA256")
    step_id = _token(step_id, "STEP_ID")
    if not isinstance(step_index, int) or isinstance(step_index, bool) or step_index < 0:
        raise LoadBearingHonestyError("STEP_INDEX_INVALID")
    if not isinstance(result, Mapping):
        raise LoadBearingHonestyError("RESULT_MAPPING_REQUIRED")
    if not isinstance(honesty_record, Mapping):
        raise LoadBearingHonestyError("HONESTY_RECORD_MAPPING_REQUIRED")

    verdict = honesty.adjudicate(honesty_record)
    if verdict.get("status") != "PASS":
        raise LoadBearingHonestyError("HONESTY_ENVELOPE_DENIED")

    result_sha = sha256_json(dict(result))
    record_sha = sha256_json(dict(honesty_record))
    verdict_sha = sha256_json(verdict)
    return {
        "schema": CERT_SCHEMA,
        "mission_id": mission_id,
        "mission_sha256": mission_sha256,
        "step_index": step_index,
        "step_id": step_id,
        "result_sha256": result_sha,
        "honesty_record_sha256": record_sha,
        "honesty_verdict_sha256": verdict_sha,
        "honesty_status": "PASS",
        "load_bearing_authorized": True,
        "certificate_only": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def validate_result_certificate(
    *,
    certificate: Mapping[str, Any],
    mission_id: str,
    mission_sha256: str,
    step_index: int,
    step_id: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(certificate, Mapping) or certificate.get("schema") != CERT_SCHEMA:
        raise LoadBearingHonestyError("CERTIFICATE_SCHEMA_INVALID")
    expected = {
        "mission_id": _token(mission_id, "MISSION_ID"),
        "mission_sha256": _token(mission_sha256, "MISSION_SHA256"),
        "step_index": step_index,
        "step_id": _token(step_id, "STEP_ID"),
        "result_sha256": sha256_json(dict(result)),
        "honesty_status": "PASS",
        "load_bearing_authorized": True,
    }
    for key, value in expected.items():
        if certificate.get(key) != value:
            raise LoadBearingHonestyError("CERTIFICATE_" + key.upper() + "_MISMATCH")
    for key in ("honesty_record_sha256", "honesty_verdict_sha256"):
        raw = certificate.get(key)
        if not isinstance(raw, str) or len(raw) != 64:
            raise LoadBearingHonestyError("CERTIFICATE_" + key.upper() + "_INVALID")
    return dict(certificate)


def certify_terminal_completion(
    *,
    mission_id: str,
    mission_sha256: str,
    state_sha256: str,
    honesty_record: Mapping[str, Any],
) -> dict[str, Any]:
    mission_id = _token(mission_id, "MISSION_ID")
    mission_sha256 = _token(mission_sha256, "MISSION_SHA256")
    state_sha256 = _token(state_sha256, "STATE_SHA256")
    if not isinstance(honesty_record, Mapping):
        raise LoadBearingHonestyError("TERMINAL_HONESTY_RECORD_REQUIRED")
    verdict = honesty.adjudicate(honesty_record)
    if verdict.get("status") != "PASS":
        raise LoadBearingHonestyError("TERMINAL_HONESTY_ENVELOPE_DENIED")
    if verdict.get("completion_claim") != "COMPLETE":
        raise LoadBearingHonestyError("TERMINAL_COMPLETION_NOT_COMPLETE")
    return {
        "schema": FINAL_SCHEMA,
        "mission_id": mission_id,
        "mission_sha256": mission_sha256,
        "state_sha256": state_sha256,
        "honesty_record_sha256": sha256_json(dict(honesty_record)),
        "honesty_verdict_sha256": sha256_json(verdict),
        "completion_claim": "COMPLETE",
        "honesty_status": "PASS",
        "terminal_completion_authorized": True,
        "certificate_only": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
