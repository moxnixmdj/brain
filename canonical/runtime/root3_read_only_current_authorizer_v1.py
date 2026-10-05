"""Exact-class semantic authorizer for the current Root3 read-only subprocess lane.

This authorizer grants only requests already classified and content-bound by
Root3 mediator V2 as READ_ONLY_DECLARED_QUERY. It creates no authority for any
other effect class. Execution remains delegated to the independently confined
read-only class executor installed by root3_strict_current_bootstrap_v1.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from canonical.runtime.root3_subprocess_final_authorizer_adapter_v2 import (
    verify_mediator_request,
)

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_CURRENT_AUTHORIZER_V1"
EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"
AUTHORITY_ID = "ROOT3_READ_ONLY_CURRENT_AUTHORITY_V1"


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


def authorize(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        req = verify_mediator_request(request)
        callsite = req["callsite"]
        if callsite["effect_class"] != EFFECT_CLASS:
            return {
                "schema": SCHEMA,
                "allowed": False,
                "reason": "EFFECT_CLASS_DENIED:" + str(callsite["effect_class"]),
                "acceptance_credit_delta": 0,
            }
        proof = {
            "schema": SCHEMA,
            "authority_id": AUTHORITY_ID,
            "mediator_request_sha256": req["request_sha256"],
            "effect_class": EFFECT_CLASS,
            "module_path": callsite["module_path"],
            "lineno": callsite["lineno"],
            "process_api": callsite["process_api"],
            "runtime_join": callsite["runtime_join"],
            "semantic_basis": (
                "EXACT_CURRENT_CALLSITE_CLASSIFICATION_PLUS_"
                "CONFINED_READ_ONLY_CLASS_EXECUTOR"
            ),
        }
        return {
            "schema": SCHEMA,
            "allowed": True,
            "authorization_sha256": _sha(proof),
            "authority_id": AUTHORITY_ID,
            "effect_class": EFFECT_CLASS,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "allowed": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
