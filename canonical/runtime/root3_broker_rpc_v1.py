from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA_REQUEST = "PROJECT_BRAIN_ROOT3_BROKER_RPC_REQUEST_V1"
SCHEMA_RESPONSE = "PROJECT_BRAIN_ROOT3_BROKER_RPC_RESPONSE_V1"
DEFAULT_MAX_FRAME_BYTES = 8_000_000


class BrokerRPCError(RuntimeError):
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


def _git_blob(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise BrokerRPCError(label + "_INVALID")
    return value


def make_request(
    *,
    driver_id: str,
    driver_contract_git_blob_sha: str,
    driver_implementation_git_blob_sha: str,
    typed_args: Any,
) -> dict[str, Any]:
    if not isinstance(driver_id, str) or not driver_id.strip() or "\x00" in driver_id:
        raise BrokerRPCError("DRIVER_ID_INVALID")
    core = {
        "schema": SCHEMA_REQUEST,
        "driver_id": driver_id.strip(),
        "driver_contract_git_blob_sha": _git_blob(
            driver_contract_git_blob_sha, "DRIVER_CONTRACT_GIT_BLOB_SHA"
        ),
        "driver_implementation_git_blob_sha": _git_blob(
            driver_implementation_git_blob_sha, "DRIVER_IMPLEMENTATION_GIT_BLOB_SHA"
        ),
        "typed_args": typed_args,
    }
    return {**core, "request_sha256": _sha(core)}


def verify_request(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokerRPCError("REQUEST_NOT_OBJECT")
    if set(value) != {
        "schema",
        "driver_id",
        "driver_contract_git_blob_sha",
        "driver_implementation_git_blob_sha",
        "typed_args",
        "request_sha256",
    }:
        raise BrokerRPCError("REQUEST_FIELDS_INVALID")
    expected = make_request(
        driver_id=value.get("driver_id"),
        driver_contract_git_blob_sha=value.get("driver_contract_git_blob_sha"),
        driver_implementation_git_blob_sha=value.get("driver_implementation_git_blob_sha"),
        typed_args=value.get("typed_args"),
    )
    if dict(value) != expected:
        raise BrokerRPCError("REQUEST_CONTENT_OR_HASH_MISMATCH")
    return expected


def make_response(
    *,
    request_sha256: str,
    ok: bool,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    if not isinstance(request_sha256, str) or len(request_sha256) != 64:
        raise BrokerRPCError("REQUEST_SHA256_INVALID")
    if not isinstance(ok, bool):
        raise BrokerRPCError("RESPONSE_OK_INVALID")
    if ok and error is not None:
        raise BrokerRPCError("SUCCESS_RESPONSE_HAS_ERROR")
    if not ok and (not isinstance(error, str) or not error):
        raise BrokerRPCError("FAILURE_RESPONSE_REQUIRES_ERROR")
    core = {
        "schema": SCHEMA_RESPONSE,
        "request_sha256": request_sha256,
        "ok": ok,
        "result": result if ok else None,
        "error": None if ok else error,
    }
    return {**core, "response_sha256": _sha(core)}


def verify_response(
    value: Mapping[str, Any],
    *,
    expected_request_sha256: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokerRPCError("RESPONSE_NOT_OBJECT")
    expected_fields = {
        "schema", "request_sha256", "ok", "result", "error", "response_sha256"
    }
    if set(value) != expected_fields:
        raise BrokerRPCError("RESPONSE_FIELDS_INVALID")
    expected = make_response(
        request_sha256=value.get("request_sha256"),
        ok=value.get("ok"),
        result=value.get("result"),
        error=value.get("error"),
    )
    if dict(value) != expected:
        raise BrokerRPCError("RESPONSE_CONTENT_OR_HASH_MISMATCH")
    if expected["request_sha256"] != expected_request_sha256:
        raise BrokerRPCError("RESPONSE_REQUEST_MISMATCH")
    return expected


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise BrokerRPCError("BROKER_EOF")
        out.extend(chunk)
    return bytes(out)


def send_frame(
    sock: socket.socket,
    value: Mapping[str, Any],
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> None:
    raw = _canon(value)
    if len(raw) > max_frame_bytes:
        raise BrokerRPCError("FRAME_TOO_LARGE")
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def recv_frame(
    sock: socket.socket,
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> dict[str, Any]:
    header = _recv_exact(sock, 4)
    (size,) = struct.unpack("!I", header)
    if size < 2 or size > max_frame_bytes:
        raise BrokerRPCError("FRAME_LENGTH_INVALID")
    raw = _recv_exact(sock, size)
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BrokerRPCError("FRAME_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise BrokerRPCError("FRAME_OBJECT_REQUIRED")
    return value


def child_roundtrip(
    fd: int,
    *,
    driver_id: str,
    driver_contract_git_blob_sha: str,
    driver_implementation_git_blob_sha: str,
    typed_args: Any,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> Any:
    if not isinstance(fd, int) or isinstance(fd, bool) or fd < 0:
        raise BrokerRPCError("BROKER_FD_INVALID")
    request = make_request(
        driver_id=driver_id,
        driver_contract_git_blob_sha=driver_contract_git_blob_sha,
        driver_implementation_git_blob_sha=driver_implementation_git_blob_sha,
        typed_args=typed_args,
    )
    dup = os.dup(fd)
    sock = socket.socket(fileno=dup)
    try:
        send_frame(sock, request, max_frame_bytes=max_frame_bytes)
        response = recv_frame(sock, max_frame_bytes=max_frame_bytes)
    finally:
        sock.close()
    verified = verify_response(
        response,
        expected_request_sha256=request["request_sha256"],
    )
    if verified["ok"] is not True:
        raise BrokerRPCError("PARENT_DENIED:" + str(verified["error"]))
    return verified["result"]


def serve_once(
    sock: socket.socket,
    handler: Callable[[dict[str, Any]], Any],
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> dict[str, Any]:
    raw = recv_frame(sock, max_frame_bytes=max_frame_bytes)
    try:
        request = verify_request(raw)
        try:
            result = handler(request)
            response = make_response(
                request_sha256=request["request_sha256"],
                ok=True,
                result=result,
            )
        except Exception as exc:
            response = make_response(
                request_sha256=request["request_sha256"],
                ok=False,
                error=type(exc).__name__ + ":" + str(exc),
            )
    except Exception:
        raise
    send_frame(sock, response, max_frame_bytes=max_frame_bytes)
    return response
