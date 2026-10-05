"""Request-bound attempt authorizer for the two currently executable Root3 classes.

This authorizer permits only coarse, content-bound attempts for:
- READ_ONLY_DECLARED_QUERY
- TEMPORARY_FILESYSTEM_TRANSFORM

It does not execute children and does not replace either class executor's deeper
path, command-semantic, output, or namespace validation. All other classes and
all malformed, drifted, or tampered requests fail closed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_transform

SCHEMA = "PROJECT_BRAIN_ROOT3_TWO_CLASS_ATTEMPT_AUTHORIZATION_V1"
AUTHORITY_ID = "ROOT3_READ_ONLY_PLUS_TEMP_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
READ_ONLY = "READ_ONLY_DECLARED_QUERY"
TEMP = "TEMPORARY_FILESYSTEM_TRANSFORM"

EXPECTED_FUNCTION = {
    ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py", 32, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/jq_query.py", 41, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 44, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py", 66, "subprocess.run"): "_run_json",
    ("canonical/runtime/bound_capabilities/yq_yaml_json.py", 21, "subprocess.run"): "run",
    temp_transform.SUPPORTED_SITE: "run",
}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
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


def _plain_argv(request: Mapping[str, Any]) -> list[str] | None:
    command = request.get("command")
    if not isinstance(command, Mapping) or command.get("kind") != "ARGV":
        return None
    items = command.get("items")
    if not isinstance(items, list) or not items:
        return None
    out: list[str] = []
    for item in items:
        if (
            not isinstance(item, Mapping)
            or item.get("kind") != "STRING"
            or not isinstance(item.get("value"), str)
            or not item.get("value")
            or "\x00" in item.get("value")
        ):
            return None
        out.append(item["value"])
    return out


def _common(request: Mapping[str, Any], key: tuple[str, int, str]) -> str | None:
    callsite = request.get("callsite")
    if callsite.get("function") != EXPECTED_FUNCTION.get(key):
        return "CALLSITE_FUNCTION_MISMATCH"
    if callsite.get("registry_site_count") != 18:
        return "REGISTRY_SITE_COUNT_MISMATCH"
    if callsite.get("runtime_join") != "EXACT_PATH_LINE_API":
        return "RUNTIME_JOIN_MISMATCH"
    if request.get("api") != "subprocess.run":
        return "PROCESS_API_MISMATCH"
    if request.get("env") is not None:
        return "CUSTOM_ENV_FORBIDDEN"
    if request.get("input") is not None:
        return "INPUT_FORBIDDEN"
    if request.get("shell") is not False:
        return "SHELL_FORBIDDEN"
    if request.get("capture_output") is not True:
        return "CAPTURE_OUTPUT_REQUIRED"
    if request.get("text") is not True and request.get("encoding") is None:
        return "TEXT_MODE_REQUIRED"
    if request.get("stdin") not in (None, "DEVNULL"):
        return "STDIN_FORBIDDEN"
    if request.get("stdout") is not None or request.get("stderr") is not None:
        return "EXPLICIT_STDOUT_STDERR_FORBIDDEN"
    if _plain_argv(request) is None:
        return "COMMAND_ITEMS_INVALID"
    return None


def _authorize_read_only(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    if key not in read_only.SUPPORTED:
        return _deny("CALLSITE_NOT_VERIFIED_READ_ONLY")
    common = _common(request, key)
    if common:
        return _deny(common)
    timeout = request.get("timeout")
    if timeout is None:
        timeout_value = 60.0
    else:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            return _deny("TIMEOUT_INVALID")
        timeout_value = float(timeout)
    if not (0.0 < timeout_value <= 180.0):
        return _deny("TIMEOUT_OUT_OF_RANGE")
    return _allow(
        request=request,
        effect_class=READ_ONLY,
        key=key,
        profile=read_only.SUPPORTED[key],
    )


def _authorize_temp(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    if key != temp_transform.SUPPORTED_SITE:
        return _deny("CALLSITE_NOT_VERIFIED_TEMP")
    common = _common(request, key)
    if common:
        return _deny(common)
    if request.get("cwd") is not None:
        return _deny("TEMP_CWD_MUST_BE_NONE")
    if request.get("timeout") != 180:
        return _deny("TEMP_TIMEOUT_MUST_EQUAL_180")
    argv = _plain_argv(request)
    assert argv is not None
    if len(argv) != 10:
        return _deny("TEMP_ARGV_LENGTH_INVALID")
    if argv[0] != "pdftoppm":
        return _deny("TEMP_EXECUTABLE_INVALID")
    if argv[1:4] != ["-f", "1", "-l"] or argv[5] != "-r" or argv[7] != "-png":
        return _deny("TEMP_OPTIONS_INVALID")
    try:
        max_pages = int(argv[4])
        dpi = int(argv[6])
    except Exception:
        return _deny("TEMP_NUMERIC_OPTIONS_INVALID")
    if not 1 <= max_pages <= 500:
        return _deny("TEMP_MAX_PAGES_OUT_OF_RANGE")
    if not 72 <= dpi <= 600:
        return _deny("TEMP_DPI_OUT_OF_RANGE")
    src = pathlib.Path(argv[8])
    prefix = pathlib.Path(argv[9])
    if not src.is_absolute() or not prefix.is_absolute():
        return _deny("TEMP_PATHS_MUST_BE_ABSOLUTE")
    if prefix.name != "page" or not prefix.parent.name.startswith("project-brain-ocr-"):
        return _deny("TEMP_OUTPUT_PREFIX_INVALID")
    return _allow(
        request=request,
        effect_class=TEMP,
        key=key,
        profile="PDF_RASTER_EPHEMERAL_OUTPUT",
    )


def _allow(
    *,
    request: Mapping[str, Any],
    effect_class: str,
    key: tuple[str, int, str],
    profile: str,
) -> dict[str, Any]:
    material = {
        "schema": SCHEMA,
        "authority_id": AUTHORITY_ID,
        "request_sha256": request["request_sha256"],
        "effect_class": effect_class,
        "callsite": {
            "module_path": key[0],
            "lineno": key[1],
            "process_api": key[2],
            "profile": profile,
        },
        "permit": "ATTEMPT_ONLY__CLASS_EXECUTOR_MUST_REVALIDATE_AND_CONFINE",
    }
    return {
        **material,
        "status": "ALLOW_REQUEST_BOUND_ROOT3_ATTEMPT",
        "allowed": True,
        "authorization_sha256": _sha(material),
        "acceptance_credit_delta": 0,
    }


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
        effect_class = callsite.get("effect_class")
        if effect_class == READ_ONLY:
            return _authorize_read_only(request, key)
        if effect_class == TEMP:
            return _authorize_temp(request, key)
        return _deny("EFFECT_CLASS_NOT_AUTHORIZED")
    except Exception as exc:
        return _deny(type(exc).__name__ + ":" + str(exc))
