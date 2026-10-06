from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import honesty_envelope_v1 as honesty
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace

CAPSULE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_EMISSION_CAPSULE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_HONESTY_EMISSION_GATEWAY_RESULT_V1"


class EmissionGatewayError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def make_capsule(
    *,
    sequence: int,
    emission_id: str,
    payload: Any,
    honesty_record: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise EmissionGatewayError("SEQUENCE_INVALID")
    if not isinstance(emission_id, str) or not emission_id.strip():
        raise EmissionGatewayError("EMISSION_ID_INVALID")
    if not isinstance(honesty_record, Mapping):
        raise EmissionGatewayError("HONESTY_RECORD_INVALID")
    record = dict(honesty_record)
    return {
        "schema": CAPSULE_SCHEMA,
        "sequence": sequence,
        "emission_id": emission_id.strip(),
        "payload": payload,
        "payload_sha256": _sha(payload),
        "honesty_record": record,
        "honesty_record_sha256": _sha(record),
    }


def encode_capsule(capsule: Mapping[str, Any]) -> bytes:
    if not isinstance(capsule, Mapping):
        raise EmissionGatewayError("CAPSULE_MAPPING_REQUIRED")
    return _canon(dict(capsule)) + b"\n"


def _parse_line(raw: str, expected_sequence: int, seen_ids: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise EmissionGatewayError("BROKER_LINE_JSON_INVALID") from exc
    if not isinstance(value, Mapping) or value.get("schema") != CAPSULE_SCHEMA:
        raise EmissionGatewayError("BROKER_LINE_NOT_EMISSION_CAPSULE")
    if value.get("sequence") != expected_sequence:
        raise EmissionGatewayError("EMISSION_SEQUENCE_NOT_CONTIGUOUS")
    emission_id = value.get("emission_id")
    if not isinstance(emission_id, str) or not emission_id.strip():
        raise EmissionGatewayError("EMISSION_ID_INVALID")
    emission_id = emission_id.strip()
    if emission_id in seen_ids:
        raise EmissionGatewayError("EMISSION_ID_DUPLICATE")
    seen_ids.add(emission_id)

    payload = value.get("payload")
    if value.get("payload_sha256") != _sha(payload):
        raise EmissionGatewayError("PAYLOAD_HASH_MISMATCH")
    record = value.get("honesty_record")
    if not isinstance(record, Mapping):
        raise EmissionGatewayError("HONESTY_RECORD_INVALID")
    if value.get("honesty_record_sha256") != _sha(record):
        raise EmissionGatewayError("HONESTY_RECORD_HASH_MISMATCH")

    try:
        verdict = honesty.adjudicate(record)
    except Exception as exc:
        raise EmissionGatewayError(
            "HONESTY_ENVELOPE_INPUT_REJECTED:" + type(exc).__name__
        ) from exc
    if verdict.get("status") != "PASS":
        raise EmissionGatewayError("HONESTY_ENVELOPE_DENIED")

    return {
        "sequence": expected_sequence,
        "emission_id": emission_id,
        "payload": payload,
        "payload_sha256": value["payload_sha256"],
        "honesty_result_sha256": _sha(verdict),
        "honesty_status": "PASS",
    }


def adjudicate_broker_payload(raw: bytes) -> list[dict[str, Any]]:
    if not isinstance(raw, bytes):
        raise EmissionGatewayError("BROKER_PAYLOAD_BYTES_REQUIRED")
    if not raw:
        return []
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EmissionGatewayError("BROKER_PAYLOAD_UTF8_INVALID") from exc
    lines = text.splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise EmissionGatewayError("BROKER_EMPTY_LINE_FORBIDDEN")
    seen_ids: set[str] = set()
    return [
        _parse_line(line, index, seen_ids)
        for index, line in enumerate(lines)
    ]


def run(
    policy: Mapping[str, Any],
    *,
    confined_runner: Callable[[Mapping[str, Any]], Mapping[str, Any]] = namespace.run_confined,
) -> dict[str, Any]:
    try:
        raw_result = confined_runner(policy)
        if not isinstance(raw_result, Mapping):
            raise EmissionGatewayError("CONFINED_RESULT_INVALID")
        status = str(raw_result.get("status") or "")
        if status == "BROKER_OUTPUT_LIMIT_EXCEEDED":
            raise EmissionGatewayError("BROKER_OUTPUT_LIMIT_EXCEEDED")
        broker = raw_result.get("broker_payload", b"")
        if not isinstance(broker, bytes):
            raise EmissionGatewayError("CONFINED_BROKER_BYTES_INVALID")
        emissions = adjudicate_broker_payload(broker)
        return {
            "schema": RESULT_SCHEMA,
            "status": (
                "PASS__ALL_EXTERNAL_EMISSIONS_HONESTY_ADJUDICATED"
                if status == "CHILD_EXITED"
                else "CHILD_NONSTANDARD_EXIT__EMISSIONS_STILL_ADJUDICATED"
            ),
            "child_status": status,
            "child_returncode": raw_result.get("returncode"),
            "policy_sha256": raw_result.get("policy_sha256"),
            "broker_bytes": raw_result.get("broker_bytes", len(broker)),
            "broker_sha256": raw_result.get(
                "broker_sha256", hashlib.sha256(broker).hexdigest()
            ),
            "emissions": emissions,
            "emission_count": len(emissions),
            "raw_broker_exposed": False,
            "stdout_exposed": False,
            "stderr_exposed": False,
            "certificate_only": True,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": RESULT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "emissions": [],
            "emission_count": 0,
            "raw_broker_exposed": False,
            "stdout_exposed": False,
            "stderr_exposed": False,
            "certificate_only": True,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
