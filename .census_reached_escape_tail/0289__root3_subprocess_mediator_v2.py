"""Class-bound fail-closed subprocess mediator V2.

V2 composes three already-separated facts:
1) the current runtime has an exact 18-site subprocess universe,
2) every site has one frozen effect class, and
3) the global subprocess choke point can recover that exact class at runtime.

A child is never launched by this module directly. After exact callsite
classification and content-bound authorization, execution is delegated only to
an explicitly bound executor for that exact effect class. Missing executors,
unknown callers, reentrant process creation, malformed authorization, and
registry drift fail closed.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import re
import subprocess
import threading
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v1 as v1
from canonical.runtime.root3_subprocess_callsite_classifier_v1 import (
    RuntimeCallsiteClassificationError,
    detect_effect_class,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import CLASSES

SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_ORIGINAL_RUN = subprocess.run
_ORIGINAL_POPEN = subprocess.Popen
_LOCK = threading.RLock()
_IN_AUTHORIZATION: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "project_brain_subprocess_v2_authorization_active", default=False
)
_IN_EXECUTOR: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "project_brain_subprocess_v2_executor_active", default=False
)
_AUTHORIZER: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None
_AUTHORITY_ID: str | None = None
_CLASS_EXECUTORS: dict[str, Callable[[Mapping[str, Any]], Any]] = {}
_INSTALLED = False


class ProcessEffectDenied(PermissionError):
    pass


class MediatorStateError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _request(
    api: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
    callsite: Mapping[str, Any],
) -> dict[str, Any]:
    # Reuse V1's closed-universe normalization for command/cwd/env/stdio and
    # process kwargs. V2 changes only the request schema and adds the exact
    # independently-derived callsite/effect-class binding.
    base = v1._request(api, args, kwargs)
    core = dict(base)
    core.pop("request_sha256", None)
    core["schema"] = SCHEMA
    core["callsite"] = {
        "module_path": str(callsite["module_path"]),
        "lineno": int(callsite["lineno"]),
        "process_api": str(callsite["process_api"]),
        "function": str(callsite["function"]),
        "effect_class": str(callsite["effect_class"]),
        "registry_site_count": int(callsite["registry_site_count"]),
        "runtime_join": str(callsite["runtime_join"]),
    }
    return {**core, "request_sha256": _sha(core)}


def _classify(api: str) -> dict[str, Any]:
    try:
        return detect_effect_class(api)
    except RuntimeCallsiteClassificationError as exc:
        raise ProcessEffectDenied(
            "SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED:" + str(exc)
        ) from exc


def _authorize(
    api: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    if _IN_AUTHORIZATION.get():
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_DURING_AUTHORIZATION_FORBIDDEN")
    if _IN_EXECUTOR.get():
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_DURING_CLASS_EXECUTOR_FORBIDDEN")
    authorizer = _AUTHORIZER
    authority_id = _AUTHORITY_ID
    if authorizer is None or authority_id is None:
        raise ProcessEffectDenied("SUBPROCESS_MEDIATOR_AUTHORIZER_NOT_BOUND")

    callsite = _classify(api)
    effect_class = str(callsite["effect_class"])
    if effect_class not in CLASSES:
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_CLASS_UNKNOWN:" + effect_class)
    request = _request(api, args, kwargs, callsite)

    token = _IN_AUTHORIZATION.set(True)
    try:
        verdict = authorizer(request)
    finally:
        _IN_AUTHORIZATION.reset(token)
    if not isinstance(verdict, Mapping):
        raise ProcessEffectDenied("SUBPROCESS_AUTHORIZER_VERDICT_INVALID")
    if verdict.get("allowed") is not True:
        raise ProcessEffectDenied(
            "SUBPROCESS_EFFECT_DENIED:" + str(verdict.get("reason") or "UNSPECIFIED")
        )
    digest = str(verdict.get("authorization_sha256") or "")
    if not SHA256_RE.fullmatch(digest):
        raise ProcessEffectDenied("SUBPROCESS_AUTHORIZATION_DIGEST_INVALID")

    return {
        "authority_id": authority_id,
        "request": request,
        "authorization_sha256": digest,
        "callsite": callsite,
        "effect_class": effect_class,
    }


def _execute(
    api: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
):
    authorization = _authorize(api, args, kwargs)
    effect_class = authorization["effect_class"]
    executor = _CLASS_EXECUTORS.get(effect_class)
    if executor is None:
        raise ProcessEffectDenied(
            "PROCESS_EFFECT_CLASS_EXECUTOR_NOT_BOUND:" + effect_class
        )
    context = {
        "api": api,
        "args": args,
        "kwargs": dict(kwargs),
        "authorization": authorization,
        "callsite": authorization["callsite"],
        "effect_class": effect_class,
    }
    token = _IN_EXECUTOR.set(True)
    try:
        return executor(context)
    finally:
        _IN_EXECUTOR.reset(token)


def _guarded_run(*args: Any, **kwargs: Any):
    return _execute("subprocess.run", args, kwargs)


def _guarded_popen(*args: Any, **kwargs: Any):
    return _execute("subprocess.Popen", args, kwargs)


def install(
    authorizer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    authority_id: str,
    class_executors: Mapping[str, Callable[[Mapping[str, Any]], Any]] | None = None,
) -> dict[str, Any]:
    global _AUTHORIZER, _AUTHORITY_ID, _CLASS_EXECUTORS, _INSTALLED
    if not callable(authorizer):
        raise MediatorStateError("SUBPROCESS_AUTHORIZER_NOT_CALLABLE")
    if not isinstance(authority_id, str) or not authority_id.strip():
        raise MediatorStateError("SUBPROCESS_AUTHORITY_ID_INVALID")
    raw = dict(class_executors or {})
    unknown = set(raw) - CLASSES
    if unknown:
        raise MediatorStateError(
            "UNKNOWN_EFFECT_CLASS_EXECUTOR:" + ",".join(sorted(unknown))
        )
    for name, executor in raw.items():
        if not callable(executor):
            raise MediatorStateError("EFFECT_CLASS_EXECUTOR_NOT_CALLABLE:" + name)

    with _LOCK:
        if _INSTALLED:
            if (
                _AUTHORIZER is authorizer
                and _AUTHORITY_ID == authority_id.strip()
                and _CLASS_EXECUTORS == raw
            ):
                return status()
            raise MediatorStateError("SUBPROCESS_MEDIATOR_ALREADY_INSTALLED")
        if subprocess.run is not _ORIGINAL_RUN:
            raise MediatorStateError("SUBPROCESS_RUN_PREEXISTING_MONKEYPATCH")
        if subprocess.Popen is not _ORIGINAL_POPEN:
            raise MediatorStateError("SUBPROCESS_POPEN_PREEXISTING_MONKEYPATCH")
        _AUTHORIZER = authorizer
        _AUTHORITY_ID = authority_id.strip()
        _CLASS_EXECUTORS = raw
        subprocess.run = _guarded_run
        subprocess.Popen = _guarded_popen
        _INSTALLED = True
        return status()


def uninstall() -> dict[str, Any]:
    global _AUTHORIZER, _AUTHORITY_ID, _CLASS_EXECUTORS, _INSTALLED
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
        _CLASS_EXECUTORS = {}
        _INSTALLED = False
        return status()


def status() -> dict[str, Any]:
    return {
        "installed": bool(_INSTALLED),
        "run_guard_active": subprocess.run is _guarded_run,
        "popen_guard_active": subprocess.Popen is _guarded_popen,
        "authority_id": _AUTHORITY_ID,
        "bound_effect_class_executors": sorted(_CLASS_EXECUTORS),
        "unbound_effect_classes": sorted(CLASSES - set(_CLASS_EXECUTORS)),
        "strict_mode_when_installed": (
            "EXACT_CALLSITE_CLASSIFICATION_PLUS_AUTHORIZATION_PLUS_"
            "EXPLICIT_CLASS_EXECUTOR_OR_DENY"
        ),
    }
