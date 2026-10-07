"""Deterministic non-creditable canary for certificate-gated router deployment."""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ROUTER_DEPLOYMENT_CANARY_V1"

def invoke(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("PAYLOAD_MAPPING_REQUIRED")
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": SCHEMA,
        "status": "PASS__DETERMINISTIC_CANARY_EXECUTED",
        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
        "terminal_result": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
