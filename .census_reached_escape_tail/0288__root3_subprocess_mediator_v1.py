"""Fail-closed global subprocess mediator for the current Project Brain runtime.

Mechanical C2 layer only. When installed, every direct call through
subprocess.run / subprocess.Popen must receive a content-bound ALLOW verdict
*before* child creation. The caller's normal return type is preserved.

This module deliberately does not manufacture authority. The supplied
authorizer must eventually be an adapter over the canonical final effect
authorizer. Until then, this is a zero-credit enforcement substrate.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import pathlib
import re
import subprocess
import threading
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_ORIGINAL_RUN = subprocess.run
_ORIGINAL_POPEN = subprocess.Popen
_LOCK = threading.RLock()
_IN_AUTHORIZATION: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "project_brain_subprocess_authorization_active",
    default=False,
)
_RUN_DELEGATING_TO_POPEN: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "project_brain_subprocess_run_delegating_to_popen",
    default=False,
)
_AUTHORIZER: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None
_AUTHORITY_ID: str | None = None
_INSTALLED = False


class ProcessEffectDenied(PermissionError):
    pass


class MediatorStateError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _command(value: Any) -> dict[str, Any]:
    if isinstance(value, (str, bytes, os.PathLike)):
        raw = os.fspath(value)
        if isinstance(raw, bytes):
            return {
                "kind": "BYTES",
                "sha256": _hash_bytes(raw),
                "bytes": len(raw),
            }
        return {"kind": "STRING", "value": str(raw)}
    if isinstance(value, (list, tuple)):
        items = []
        for item in value:
            if isinstance(item, bytes):
                items.append({
                    "kind": "BYTES",
                    "sha256": _hash_bytes(item),
                    "bytes": len(item),
                })
            elif isinstance(item, (str, os.PathLike)):
                items.append({"kind": "STRING", "value": os.fspath(item)})
            else:
                raise ProcessEffectDenied(
                    "SUBPROCESS_COMMAND_ELEMENT_TYPE_UNSUPPORTED:"
                    + type(item).__name__
                )
        return {"kind": "ARGV", "items": items}
    raise ProcessEffectDenied(
        "SUBPROCESS_COMMAND_TYPE_UNSUPPORTED:" + type(value).__name__
    )


def _stdio_token(value: Any, label: str) -> str | int | None:
    if value is None:
        return None
    allowed = {
        subprocess.PIPE: "PIPE",
        subprocess.DEVNULL: "DEVNULL",
        subprocess.STDOUT: "STDOUT",
    }
    if value in allowed:
        return allowed[value]
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ProcessEffectDenied(label + "_UNSUPPORTED_FOR_STRICT_MEDIATION")


def _environment(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ProcessEffectDenied("SUBPROCESS_ENV_NOT_MAPPING")
    normalized = []
    for key, val in value.items():
        if not isinstance(key, str):
            raise ProcessEffectDenied("SUBPROCESS_ENV_KEY_NOT_STRING")
        if not isinstance(val, (str, bytes, os.PathLike)):
            raise ProcessEffectDenied(
                "SUBPROCESS_ENV_VALUE_TYPE_UNSUPPORTED:" + key
            )
        raw = os.fspath(val)
        if isinstance(raw, bytes):
            encoded = {"bytes_sha256": _hash_bytes(raw), "bytes": len(raw)}
        else:
            encoded = {"value_sha256": _hash_bytes(str(raw).encode("utf-8"))}
        normalized.append({"key": key, **encoded})
    normalized.sort(key=lambda x: x["key"])
    return {
        "key_count": len(normalized),
        "binding_sha256": _hash_bytes(_canon(normalized)),
    }


_REQUEST_BOUND_KWARGS = {
    "cwd", "env", "stdin", "stdout", "stderr", "input", "shell", "text",
    "universal_newlines", "capture_output", "timeout", "encoding", "errors",
    "close_fds",
}
_CALLER_ONLY_KWARGS = {"check", "bufsize"}
_FORBIDDEN_PROCESS_KWARGS = {
    "executable", "preexec_fn", "pass_fds", "restore_signals",
    "start_new_session", "process_group", "user", "group", "extra_groups",
    "umask", "creationflags", "startupinfo", "pipesize",
}


def _reject_unsupported_kwargs(kwargs: Mapping[str, Any]) -> None:
    # Closed-universe rule: no subprocess launch knob may be silently omitted
    # from the request digest. New knobs must be explicitly classified.
    for key, value in kwargs.items():
        if key in _REQUEST_BOUND_KWARGS or key in _CALLER_ONLY_KWARGS:
            continue
        if key in _FORBIDDEN_PROCESS_KWARGS:
            if value not in (None, False, 0, (), []):
                raise ProcessEffectDenied(
                    "SUBPROCESS_KWARG_NOT_YET_MEDIATED:" + key
                )
            continue
        raise ProcessEffectDenied("SUBPROCESS_KWARG_UNCLASSIFIED:" + key)


def _request(api: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if not args:
        raise ProcessEffectDenied("SUBPROCESS_COMMAND_REQUIRED")
    if len(args) != 1:
        raise ProcessEffectDenied(
            "SUBPROCESS_POSITIONAL_ARGUMENTS_BEYOND_COMMAND_FORBIDDEN"
        )
    _reject_unsupported_kwargs(kwargs)

    cwd = kwargs.get("cwd")
    if cwd is not None:
        try:
            cwd = os.fspath(cwd)
        except TypeError as exc:
            raise ProcessEffectDenied("SUBPROCESS_CWD_INVALID") from exc
        if isinstance(cwd, bytes):
            cwd_binding: Any = {
                "bytes_sha256": _hash_bytes(cwd),
                "bytes": len(cwd),
            }
        else:
            cwd_binding = str(pathlib.Path(cwd))
    else:
        cwd_binding = None

    input_value = kwargs.get("input")
    if input_value is None:
        input_binding = None
    elif isinstance(input_value, str):
        raw = input_value.encode("utf-8")
        input_binding = {"sha256": _hash_bytes(raw), "bytes": len(raw), "type": "TEXT"}
    elif isinstance(input_value, (bytes, bytearray)):
        raw = bytes(input_value)
        input_binding = {"sha256": _hash_bytes(raw), "bytes": len(raw), "type": "BYTES"}
    else:
        raise ProcessEffectDenied("SUBPROCESS_INPUT_TYPE_UNSUPPORTED")

    core = {
        "schema": SCHEMA,
        "api": api,
        "command": _command(args[0]),
        "cwd": cwd_binding,
        "env": _environment(kwargs.get("env")),
        "stdin": _stdio_token(kwargs.get("stdin"), "SUBPROCESS_STDIN"),
        "stdout": _stdio_token(kwargs.get("stdout"), "SUBPROCESS_STDOUT"),
        "stderr": _stdio_token(kwargs.get("stderr"), "SUBPROCESS_STDERR"),
        "input": input_binding,
        "shell": bool(kwargs.get("shell", False)),
        "text": bool(
            kwargs.get("text", False)
            or kwargs.get("universal_newlines", False)
        ),
        "capture_output": bool(kwargs.get("capture_output", False)),
        "timeout": kwargs.get("timeout"),
        "encoding": kwargs.get("encoding"),
        "errors": kwargs.get("errors"),
        "close_fds": kwargs.get("close_fds"),
    }
    raw = _canon(core)
    return {
        **core,
        "request_sha256": _hash_bytes(raw),
    }


def _authorize(api: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    authorizer = _AUTHORIZER
    authority_id = _AUTHORITY_ID
    if authorizer is None or authority_id is None:
        raise ProcessEffectDenied("SUBPROCESS_MEDIATOR_AUTHORIZER_NOT_BOUND")
    if _IN_AUTHORIZATION.get():
        raise ProcessEffectDenied(
            "SUBPROCESS_EFFECT_DURING_AUTHORIZATION_FORBIDDEN"
        )
    request = _request(api, args, kwargs)
    token = _IN_AUTHORIZATION.set(True)
    try:
        verdict = authorizer(request)
    finally:
        _IN_AUTHORIZATION.reset(token)
    if not isinstance(verdict, Mapping):
        raise ProcessEffectDenied("SUBPROCESS_AUTHORIZER_VERDICT_INVALID")
    if verdict.get("allowed") is not True:
        raise ProcessEffectDenied(
            "SUBPROCESS_EFFECT_DENIED:"
            + str(verdict.get("reason") or "UNSPECIFIED")
        )
    digest = str(verdict.get("authorization_sha256") or "")
    if not SHA256_RE.fullmatch(digest):
        raise ProcessEffectDenied(
            "SUBPROCESS_AUTHORIZATION_DIGEST_INVALID"
        )
    return {
        "authority_id": authority_id,
        "request": request,
        "authorization_sha256": digest,
    }


def _guarded_run(*args: Any, **kwargs: Any):
    _authorize("subprocess.run", args, kwargs)
    token = _RUN_DELEGATING_TO_POPEN.set(True)
    try:
        return _ORIGINAL_RUN(*args, **kwargs)
    finally:
        _RUN_DELEGATING_TO_POPEN.reset(token)


def _guarded_popen(*args: Any, **kwargs: Any):
    if _RUN_DELEGATING_TO_POPEN.get():
        return _ORIGINAL_POPEN(*args, **kwargs)
    _authorize("subprocess.Popen", args, kwargs)
    return _ORIGINAL_POPEN(*args, **kwargs)


def install(
    authorizer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    authority_id: str,
) -> dict[str, Any]:
    global _AUTHORIZER, _AUTHORITY_ID, _INSTALLED
    if not callable(authorizer):
        raise MediatorStateError("SUBPROCESS_AUTHORIZER_NOT_CALLABLE")
    if not isinstance(authority_id, str) or not authority_id.strip():
        raise MediatorStateError("SUBPROCESS_AUTHORITY_ID_INVALID")
    with _LOCK:
        if _INSTALLED:
            if _AUTHORIZER is authorizer and _AUTHORITY_ID == authority_id:
                return status()
            raise MediatorStateError("SUBPROCESS_MEDIATOR_ALREADY_INSTALLED")
        if subprocess.run is not _ORIGINAL_RUN:
            raise MediatorStateError(
                "SUBPROCESS_RUN_PREEXISTING_MONKEYPATCH"
            )
        if subprocess.Popen is not _ORIGINAL_POPEN:
            raise MediatorStateError(
                "SUBPROCESS_POPEN_PREEXISTING_MONKEYPATCH"
            )
        _AUTHORIZER = authorizer
        _AUTHORITY_ID = authority_id.strip()
        subprocess.run = _guarded_run
        subprocess.Popen = _guarded_popen
        _INSTALLED = True
        return status()


def uninstall() -> dict[str, Any]:
    global _AUTHORIZER, _AUTHORITY_ID, _INSTALLED
    with _LOCK:
        if not _INSTALLED:
            return status()
        if subprocess.run is not _guarded_run:
            raise MediatorStateError("SUBPROCESS_RUN_GUARD_REPLACED")
        if subprocess.Popen is not _guarded_popen:
            raise MediatorStateError("SUBPROCESS_POPEN_GUARD_REPLACED")
        subprocess.run = _ORIGINAL_RUN
        subprocess.Popen = _ORIGINAL_POPEN
        _AUTHORIZER = None
        _AUTHORITY_ID = None
        _INSTALLED = False
        return status()


def status() -> dict[str, Any]:
    return {
        "installed": bool(_INSTALLED),
        "run_guard_active": subprocess.run is _guarded_run,
        "popen_guard_active": subprocess.Popen is _guarded_popen,
        "authority_id": _AUTHORITY_ID,
        "default_without_install": "UNCHANGED",
        "strict_mode_when_installed": "FAIL_CLOSED_PRE_CHILD_AUTHORIZATION",
    }
