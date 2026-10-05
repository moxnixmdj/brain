"""Deterministic semantic authorizer for the verified read-only subprocess class.

This authorizer grants only a request-bound attempt permit for the exact
READ_ONLY_DECLARED_QUERY callsites that already have a confined executor.
It does not execute a child and does not replace the executor's deeper
command/filter/path validation.

All other effect classes, unknown callsites, malformed request hashes, custom
environment/input, shell execution, non-captured output, and unbounded timeout
fail closed.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_ATTEMPT_AUTHORIZATION_V1"
AUTHORITY_ID = "ROOT3_READ_ONLY_DECLARED_QUERY_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"


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


def _deny(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "DENY_FAIL_CLOSED",
        "allowed": False,
        "reason": reason,
        "acceptance_credit_delta": 0,
    }


def _request_hash_valid(request: Mapping[str, Any]) -> bool:
    digest = request.get("request_sha256")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        return False
    core = dict(request)
    core.pop("request_sha256", None)
    return hashlib.sha256(_canon(core)).hexdigest() == digest


def authorize(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            return _deny("REQUEST_NOT_MAPPING")
        if request.get("schema") != mediator.SCHEMA:
            return _deny("REQUEST_SCHEMA_MISMATCH")
        if not _request_hash_valid(request):
            return _deny("REQUEST_HASH_MISMATCH")

        callsite = request.get("callsite")
        if not isinstance(callsite, Mapping):
            return _deny("CALLSITE_MISSING")
        key = (
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
        if key not in read_only.SUPPORTED:
            return _deny("CALLSITE_NOT_VERIFIED_READ_ONLY")
        if callsite.get("effect_class") != EFFECT_CLASS:
            return _deny("EFFECT_CLASS_MISMATCH")
        if request.get("api") != "subprocess.run":
            return _deny("PROCESS_API_MISMATCH")

        command = request.get("command")
        if not isinstance(command, Mapping) or command.get("kind") != "ARGV":
            return _deny("COMMAND_NOT_ARGV")
        items = command.get("items")
        if not isinstance(items, list) or not items:
            return _deny("COMMAND_ITEMS_INVALID")
        for item in items:
            if (
                not isinstance(item, Mapping)
                or item.get("kind") != "STRING"
                or not isinstance(item.get("value"), str)
                or not item.get("value")
                or "\x00" in item.get("value")
            ):
                return _deny("COMMAND_ITEM_NOT_PLAIN_STRING")

        if request.get("env") is not None:
            return _deny("CUSTOM_ENV_FORBIDDEN")
        if request.get("input") is not None:
            return _deny("INPUT_FORBIDDEN")
        if request.get("shell") is not False:
            return _deny("SHELL_FORBIDDEN")
        if request.get("capture_output") is not True:
            return _deny("CAPTURE_OUTPUT_REQUIRED")
        if request.get("text") is not True and request.get("encoding") is None:
            return _deny("TEXT_MODE_REQUIRED")
        if request.get("stdin") not in (None, "DEVNULL"):
            return _deny("STDIN_FORBIDDEN")

        timeout = request.get("timeout")
        if timeout is None:
            timeout_value = 60.0
        else:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                return _deny("TIMEOUT_INVALID")
            timeout_value = float(timeout)
        if not (0.0 < timeout_value <= 180.0):
            return _deny("TIMEOUT_OUT_OF_RANGE")

        material = {
            "schema": SCHEMA,
            "authority_id": AUTHORITY_ID,
            "request_sha256": request["request_sha256"],
            "effect_class": EFFECT_CLASS,
            "callsite": {
                "module_path": key[0],
                "lineno": key[1],
                "process_api": key[2],
                "profile": read_only.SUPPORTED[key],
            },
            "permit": "ATTEMPT_ONLY__EXECUTOR_MUST_REVALIDATE_AND_CONFINE",
        }
        return {
            **material,
            "status": "ALLOW_REQUEST_BOUND_READ_ONLY_ATTEMPT",
            "allowed": True,
            "authorization_sha256": _sha(material),
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return _deny(type(exc).__name__ + ":" + str(exc))
