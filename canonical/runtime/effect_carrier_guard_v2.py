"""Truth-preserving carrier guard for Project Brain side effects.

V2 repairs a critical observability hole in V1: once a carrier has been invoked,
receipt serialization can no longer make the system report a clean pre-effect
denial. Carrier exceptions and result-binding failures are represented as
post-invocation states with explicit uncertainty.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect

SCHEMA = "PROJECT_BRAIN_EFFECT_CARRIER_GUARD_V2"
MAX_BOUND_RESULT_BYTES = 8_000_000


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _pre_effect_deny(authorization: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "DENY_NO_CARRIER_INVOCATION",
        "carrier_invoked": False,
        "carrier_returned": False,
        "effect_completion": "NOT_ATTEMPTED",
        "authorization": dict(authorization),
        "acceptance_credit_delta": 0,
    }


def execute_authorized_effect(
    request: Mapping[str, Any],
    grant: Mapping[str, Any],
    *,
    repo_root: str | Path,
    carrier: Callable[[Mapping[str, Any]], Any],
) -> dict[str, Any]:
    authorization = authorize_effect(request, grant, repo_root=repo_root)
    if (
        authorization.get("allowed") is not True
        or authorization.get("status") != "ALLOW_FINAL_AUTHORIZATION"
    ):
        return _pre_effect_deny(authorization)

    try:
        result = carrier(request)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "CARRIER_EXCEPTION_AFTER_INVOCATION",
            "carrier_invoked": True,
            "carrier_returned": False,
            "effect_completion": "UNKNOWN_MAY_HAVE_PARTIALLY_OCCURRED",
            "request_sha256": authorization["request_sha256"],
            "grant_sha256": authorization["grant_sha256"],
            "authorization": authorization,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)[:2000],
            "manual_or_domain_specific_reconciliation_required": True,
            "acceptance_credit_delta": 0,
        }

    try:
        result_bytes = _canon(result)
        if len(result_bytes) > MAX_BOUND_RESULT_BYTES:
            raise ValueError("CARRIER_RESULT_TOO_LARGE")
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "CARRIER_RETURNED_RESULT_BINDING_FAILED",
            "carrier_invoked": True,
            "carrier_returned": True,
            "effect_completion": "CARRIER_RETURNED_EFFECT_STATE_REQUIRES_RECONCILIATION",
            "request_sha256": authorization["request_sha256"],
            "grant_sha256": authorization["grant_sha256"],
            "authorization": authorization,
            "binding_error_type": type(exc).__name__,
            "binding_error_message": str(exc)[:2000],
            "manual_or_domain_specific_reconciliation_required": True,
            "acceptance_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "CARRIER_RETURNED_WITH_BOUND_RESULT",
        "carrier_invoked": True,
        "carrier_returned": True,
        "effect_completion": "CARRIER_RETURNED_RESULT_CONTENT_BOUND",
        "request_sha256": authorization["request_sha256"],
        "grant_sha256": authorization["grant_sha256"],
        "effect_kind": authorization["effect_kind"],
        "resource": authorization["resource"],
        "operation": authorization["operation"],
        "payload_sha256": authorization["payload_sha256"],
        "authorization": authorization,
        "carrier_result_sha256": result_sha256,
        "carrier_result_bytes": len(result_bytes),
        "carrier_result": result,
        "repository_wide_exclusivity_still_required": True,
        "domain_specific_postcondition_verification_still_required": True,
        "acceptance_credit_delta": 0,
    }
