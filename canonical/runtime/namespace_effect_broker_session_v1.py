#!/usr/bin/env python3
"""Parent-side broker session for namespace-confined Brain workers.

The child can submit typed effect requests over its single broker socket. The
parent validates the exact request, obtains a grant from an explicit provider,
runs the canonical final authorizer, and only then dispatches to an explicitly
bound parent-side effect handler.

This module itself grants no effect authority.
"""
from __future__ import annotations

import hashlib
import json
import socket
import struct
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime.effect_broker_contract_v1 import verify_request
from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect

SCHEMA = "PROJECT_BRAIN_NAMESPACE_EFFECT_BROKER_SESSION_V1"
MAX_FRAME_BYTES = 8_100_000


class BrokerSessionError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _read_exact(sock: socket.socket, n: int) -> bytes:
    chunks: list[bytes] = []
    remaining = n
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise BrokerSessionError("TRUNCATED_FRAME")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_frame(sock: socket.socket) -> dict[str, Any] | None:
    first = sock.recv(4)
    if not first:
        return None
    if len(first) < 4:
        first += _read_exact(sock, 4 - len(first))
    (size,) = struct.unpack(">I", first)
    if size < 2 or size > MAX_FRAME_BYTES:
        raise BrokerSessionError("FRAME_SIZE_INVALID")
    raw = _read_exact(sock, size)
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BrokerSessionError("FRAME_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise BrokerSessionError("FRAME_NOT_OBJECT")
    return value


def send_frame(sock: socket.socket, value: Mapping[str, Any]) -> None:
    raw = _canon(dict(value))
    if len(raw) > MAX_FRAME_BYTES:
        raise BrokerSessionError("RESPONSE_FRAME_TOO_LARGE")
    sock.sendall(struct.pack(">I", len(raw)) + raw)


def process_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    grant_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    effect_handlers: Mapping[
        tuple[str, str],
        Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    ],
    authorizer: Callable[..., Mapping[str, Any]] = authorize_effect,
) -> dict[str, Any]:
    try:
        req = verify_request(request)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }

    try:
        grant = grant_provider(req)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "reason": "GRANT_PROVIDER:" + type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }

    try:
        verdict = dict(authorizer(req, grant, repo_root=repo_root))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "reason": "FINAL_AUTHORIZER:" + type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }

    verdict_sha = _sha(verdict)
    if (
        verdict.get("allowed") is not True
        or verdict.get("status") != "ALLOW_FINAL_AUTHORIZATION"
    ):
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "final_authorization_sha256": verdict_sha,
            "authorization": verdict,
            "acceptance_credit_delta": 0,
        }

    if verdict.get("effect_carrier_atomic_enforcement_still_required") is not True:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "final_authorization_sha256": verdict_sha,
            "reason": "CARRIER_ATOMIC_ENFORCEMENT_FLAG_MISSING",
            "acceptance_credit_delta": 0,
        }

    key = (str(req["effect_kind"]), str(req["operation"]))
    handler = effect_handlers.get(key)
    if handler is None:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "final_authorization_sha256": verdict_sha,
            "reason": "NO_BOUND_EFFECT_HANDLER:" + key[0] + ":" + key[1],
            "acceptance_credit_delta": 0,
        }

    try:
        result = handler(req, verdict)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "final_authorization_sha256": verdict_sha,
            "reason": "EFFECT_HANDLER:" + type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
    if not isinstance(result, Mapping):
        return {
            "schema": SCHEMA,
            "status": "DENY_FAIL_CLOSED",
            "effect_executed": False,
            "request_sha256": req["request_sha256"],
            "final_authorization_sha256": verdict_sha,
            "reason": "EFFECT_HANDLER_RESULT_NOT_OBJECT",
            "acceptance_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "APPLIED_AUTHORIZED_EFFECT",
        "effect_executed": True,
        "request_sha256": req["request_sha256"],
        "final_authorization_sha256": verdict_sha,
        "effect_kind": req["effect_kind"],
        "operation": req["operation"],
        "effect_result": dict(result),
        "acceptance_credit_delta": 0,
    }


def serve_broker_session(
    sock: socket.socket,
    *,
    repo_root: str | Path,
    grant_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    effect_handlers: Mapping[
        tuple[str, str],
        Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    ],
    max_requests: int = 256,
) -> dict[str, Any]:
    if not 1 <= int(max_requests) <= 4096:
        raise BrokerSessionError("MAX_REQUESTS_INVALID")
    rows: list[dict[str, Any]] = []
    for _ in range(int(max_requests)):
        request = recv_frame(sock)
        if request is None:
            return {
                "schema": SCHEMA,
                "status": "SESSION_CLOSED",
                "request_count": len(rows),
                "applied_count": sum(
                    1 for row in rows if row.get("effect_executed") is True
                ),
                "denied_count": sum(
                    1 for row in rows if row.get("effect_executed") is not True
                ),
                "responses": rows,
                "acceptance_credit_delta": 0,
            }
        response = process_request(
            request,
            repo_root=repo_root,
            grant_provider=grant_provider,
            effect_handlers=effect_handlers,
        )
        send_frame(sock, response)
        rows.append(response)
    raise BrokerSessionError("REQUEST_LIMIT_EXCEEDED")
