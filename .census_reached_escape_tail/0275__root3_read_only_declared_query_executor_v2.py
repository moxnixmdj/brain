from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as v1

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_DECLARED_QUERY_EXECUTOR_V2"
EFFECT_CLASS = v1.EFFECT_CLASS

APT_SUPPORTED = {
    ("canonical/runtime/capability_discovery.py", 267, "subprocess.run"): "APT_SEARCH",
    ("canonical/runtime/capability_discovery.py", 359, "subprocess.run"): "APT_POLICY",
    ("canonical/runtime/capability_discovery.py", 368, "subprocess.run"): "APT_SHOW",
}
SUPPORTED = {**v1.SUPPORTED, **APT_SUPPORTED}

_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,127}(?::[a-z0-9][a-z0-9-]{0,31})?$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+:~_-]{0,255}$")
_QUERY_RE = re.compile(r"^[a-z0-9][a-z0-9 -]{0,127}$")


class ReadOnlyQueryDenied(v1.ReadOnlyQueryDenied):
    pass


def _callsite_key(context: Mapping[str, Any]) -> tuple[str, int, str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise ReadOnlyQueryDenied("EFFECT_CLASS_MISMATCH")
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise ReadOnlyQueryDenied("CALLSITE_MISSING")
    try:
        return (
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
    except Exception as exc:
        raise ReadOnlyQueryDenied("CALLSITE_INVALID") from exc


def _validate_apt_common(context: Mapping[str, Any]) -> tuple[list[str], dict[str, Any], tuple[str, int, str], str]:
    key = _callsite_key(context)
    profile = APT_SUPPORTED.get(key)
    if profile is None:
        raise ReadOnlyQueryDenied("APT_CALLSITE_NOT_SUPPORTED:" + repr(key))
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise ReadOnlyQueryDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (list, tuple)) or not command:
        raise ReadOnlyQueryDenied("COMMAND_ARGV_REQUIRED")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    kwargs = dict(context.get("kwargs") or {})
    if set(kwargs) - {"text", "capture_output", "timeout"}:
        raise ReadOnlyQueryDenied("APT_KWARGS_NOT_EXACT")
    if kwargs.get("text") is not True or kwargs.get("capture_output") is not True:
        raise ReadOnlyQueryDenied("APT_TEXT_CAPTURE_REQUIRED")
    if kwargs.get("timeout") is None:
        raise ReadOnlyQueryDenied("APT_TIMEOUT_REQUIRED")
    v1._timeout(kwargs, maximum=60)
    return argv, kwargs, key, profile


def _copy_regular_files(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src.iterdir(), key=lambda p: p.name):
        if entry.name == "lock" or not entry.is_file():
            continue
        target = dst / entry.name
        shutil.copy2(entry, target, follow_symlinks=True)
        if not target.is_file():
            raise ReadOnlyQueryDenied("APT_SNAPSHOT_COPY_NOT_FILE:" + entry.name)


def _make_apt_snapshot() -> pathlib.Path:
    lists = pathlib.Path("/var/lib/apt/lists")
    status = pathlib.Path("/var/lib/dpkg/status")
    etc_apt = pathlib.Path("/etc/apt")
    if not lists.is_dir() or not status.is_file() or not etc_apt.is_dir():
        raise ReadOnlyQueryDenied("APT_METADATA_SOURCE_UNAVAILABLE")
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-apt-readonly-snapshot-"))
    try:
        _copy_regular_files(lists, root / "lists")
        dpkg = root / "dpkg"
        dpkg.mkdir()
        shutil.copy2(status, dpkg / "status")
        extended = pathlib.Path("/var/lib/apt/extended_states")
        if extended.is_file():
            shutil.copy2(extended, root / "extended_states")
        else:
            (root / "extended_states").write_bytes(b"")
        shutil.copytree(etc_apt, root / "etc" / "apt", symlinks=False)
        return root
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _apt_options() -> list[str]:
    return [
        "-o", "Dir::State::lists=/input/lists",
        "-o", "Dir::State::status=/input/dpkg/status",
        "-o", "Dir::State::extended_states=/input/extended_states",
        "-o", "Dir::Etc=/input/etc/apt/",
        "-o", "Dir::Cache::pkgcache=",
        "-o", "Dir::Cache::srcpkgcache=",
    ]


def _prepare_apt(context: Mapping[str, Any]) -> dict[str, Any]:
    argv, kwargs, key, profile = _validate_apt_common(context)
    exe = v1._resolve_executable(argv[0], {"apt-cache"})
    if profile == "APT_SEARCH":
        if len(argv) != 3 or argv[1] != "search" or not _QUERY_RE.fullmatch(argv[2]):
            raise ReadOnlyQueryDenied("APT_SEARCH_SHAPE_OR_QUERY_INVALID")
        inner = [exe, *_apt_options(), "search", argv[2]]
    elif profile == "APT_POLICY":
        if len(argv) != 3 or argv[1] != "policy" or not _PACKAGE_RE.fullmatch(argv[2]):
            raise ReadOnlyQueryDenied("APT_POLICY_SHAPE_OR_PACKAGE_INVALID")
        inner = [exe, *_apt_options(), "policy", argv[2]]
    elif profile == "APT_SHOW":
        if len(argv) != 3 or argv[1] != "show" or argv[2].count("=") != 1:
            raise ReadOnlyQueryDenied("APT_SHOW_SHAPE_INVALID")
        package, version = argv[2].split("=", 1)
        if not _PACKAGE_RE.fullmatch(package) or not _VERSION_RE.fullmatch(version):
            raise ReadOnlyQueryDenied("APT_SHOW_PACKAGE_OR_VERSION_INVALID")
        inner = [exe, *_apt_options(), "show", package + "=" + version]
    else:
        raise ReadOnlyQueryDenied("APT_PROFILE_UNREACHABLE")

    snapshot = _make_apt_snapshot()
    timeout = v1._timeout(kwargs, maximum=60)
    spec = {"argv": inner, "cwd": "/input", "timeout": timeout}
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    policy = {
        "argv": ["/usr/bin/python3", "-I", "-c", v1._WRAPPER, encoded],
        "input_dir": str(snapshot),
        "limits": {
            "pids": 32,
            "memory_mb": 1024,
            "cpu_seconds": max(1, min(int(timeout) + 1, 300)),
            "wallclock_s": max(1, min(int(timeout) + 5, 600)),
            "scratch_mb": 64,
            "max_file_mb": 16,
            "nofile": 64,
            "broker_max_bytes": 8_000_000,
        },
    }
    return {
        "profile": profile,
        "callsite_key": key,
        "original_argv": argv,
        "kwargs": kwargs,
        "policy": policy,
        "timeout": timeout,
        "cleanup_dir": str(snapshot),
    }


def _completed(prepared: Mapping[str, Any], result: Mapping[str, Any]) -> subprocess.CompletedProcess[str]:
    stdout_b = base64.b64decode(result.get("stdout_b64") or "")
    stderr_b = base64.b64decode(result.get("stderr_b64") or "")
    if result.get("timed_out"):
        raise subprocess.TimeoutExpired(
            prepared["original_argv"],
            prepared["timeout"],
            output=stdout_b,
            stderr=stderr_b,
        )
    kwargs = prepared["kwargs"]
    encoding = kwargs.get("encoding") or "utf-8"
    errors = kwargs.get("errors") or "strict"
    stdout = stdout_b.decode(encoding, errors=errors)
    stderr = stderr_b.decode(encoding, errors=errors)
    if prepared.get("profile") == "APT_POLICY":
        stdout = stdout.replace("/input/dpkg/status", "/var/lib/dpkg/status")
    return subprocess.CompletedProcess(
        args=prepared["original_argv"],
        returncode=int(result["returncode"]),
        stdout=stdout,
        stderr=stderr,
    )


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")
    v1_executor = v1.make_executor(popen_impl=popen_impl)

    def execute(context: Mapping[str, Any]) -> Any:
        key = _callsite_key(context)
        if key not in APT_SUPPORTED:
            return v1_executor(context)
        prepared = _prepare_apt(context)
        try:
            result = v1._run_confined_with_popen(prepared["policy"], popen_impl)
            return _completed(prepared, result)
        finally:
            shutil.rmtree(prepared["cleanup_dir"], ignore_errors=True)

    return execute
