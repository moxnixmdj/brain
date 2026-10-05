"""Atomic local carrier guard for Project Brain side effects.

The supplied carrier callable is invoked only after the composed final
authorization returns ALLOW_FINAL_AUTHORIZATION. The module then binds the
carrier result to the exact request/grant authorization. This proves no bypass
inside this call boundary; repository-wide exclusivity remains a separate audit.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect

SCHEMA = "PROJECT_BRAIN_EFFECT_CARRIER_GUARD_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def execute_authorized_effect(
    request: Mapping[str, Any],
    grant: Mapping[str, Any],
    *,
    repo_root: str | Path,
    carrier: Callable[[Mapping[str, Any]], Any],
) -> dict[str, Any]:
    """Authorize, then invoke exactly one carrier call if and only if allowed."""
    authorization = authorize_effect(request, grant, repo_root=repo_root)
    if authorization.get("allowed") is not True:
        return {
            "schema": SCHEMA,
            "status": "DENY_NO_EFFECT",
            "effect_executed": False,
            "authorization": authorization,
            "acceptance_credit_delta": 0,
        }
    if authorization.get("status") != "ALLOW_FINAL_AUTHORIZATION":
        return {
            "schema": SCHEMA,
            "status": "DENY_NO_EFFECT",
            "effect_executed": False,
            "authorization": {
                "allowed": False,
                "reason": "NONFINAL_ALLOW_STATUS",
            },
            "acceptance_credit_delta": 0,
        }

    result = carrier(request)
    result_sha256 = hashlib.sha256(_canon(result)).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "EFFECT_EXECUTED_AFTER_FINAL_AUTHORIZATION",
        "effect_executed": True,
        "request_sha256": authorization["request_sha256"],
        "grant_sha256": authorization["grant_sha256"],
        "effect_kind": authorization["effect_kind"],
        "resource": authorization["resource"],
        "operation": authorization["operation"],
        "payload_sha256": authorization["payload_sha256"],
        "authorization": authorization,
        "carrier_result_sha256": result_sha256,
        "carrier_result": result,
        "repository_wide_exclusivity_still_required": True,
        "acceptance_credit_delta": 0,
    }
