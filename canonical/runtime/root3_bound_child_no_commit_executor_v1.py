from __future__ import annotations

import base64
import json
import math
import os
import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as confined

SCHEMA = "PROJECT_BRAIN_ROOT3_BOUND_CHILD_NO_COMMIT_EXECUTOR_V1"
EFFECT_CLASS = "BOUND_CHILD_CODE_EXECUTION"

SUPPORTED = {
    ("canonical/runtime/astra_runtime.py", 1215, "subprocess.run"): "REPO_PYTHON_VERIFICATION",
    ("canonical/runtime/auto_python_source_codec_acquisition.py", 217, "subprocess.run"): "PYTHON_SOURCE_CODEC_PROBE",
    ("canonical/runtime/bound_capabilities/python_test_audit.py", 50, "subprocess.run"): "REPO_PYTHON_TEST_AUDIT",
}

_WRAPPER = r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
cwd=spec.get("cwd")
if cwd:
    os.chdir(cwd)
env=os.environ.copy()
for k,v in (spec.get("env_add") or {}).items():
    env[str(k)]=str(v)
try:
    p=subprocess.run(
        spec["argv"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=spec["timeout"],
        check=False,
        env=env,
    )
    out={
        "timed_out":False,
        "returncode":int(p.returncode),
        "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
    }
except subprocess.TimeoutExpired as exc:
    out={
        "timed_out":True,
        "returncode":None,
        "stdout_b64":base64.b64encode(exc.output or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(exc.stderr or b"").decode("ascii"),
    }
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""


class BoundChildDenied(PermissionError):
    pass


def _key(context: Mapping[str, Any]) -> tuple[str, int, str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise BoundChildDenied("EFFECT_CLASS_MISMATCH")
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise BoundChildDenied("CALLSITE_MISSING")
    try:
        key = (
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
    except Exception as exc:
        raise BoundChildDenied("CALLSITE_INVALID") from exc
    if key not in SUPPORTED:
        raise BoundChildDenied("BOUND_CHILD_CALLSITE_NOT_SUPPORTED:" + repr(key))
    return key


def _path(value: Any) -> pathlib.Path:
    try:
        return pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc:
        raise BoundChildDenied("PATH_INVALID") from exc


def _inside(root: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    try:
        return target.relative_to(root)
    except ValueError as exc:
        raise BoundChildDenied("PATH_OUTSIDE_DECLARED_ROOT") from exc


def _argv(context: Mapping[str, Any]) -> tuple[list[str], dict[str, Any], tuple[str, int, str], str]:
    key = _key(context)
    args = context.get("args")
    if not isinstance(args, (tuple, list)) or len(args) != 1:
        raise BoundChildDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (tuple, list)) or not command:
        raise BoundChildDenied("COMMAND_ARGV_REQUIRED")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    kwargs = dict(context.get("kwargs") or {})
    allowed = {"cwd", "text", "capture_output", "timeout", "env", "check"}
    extra = set(kwargs) - allowed
    if extra:
        raise BoundChildDenied("KWARGS_NOT_EXACT:" + ",".join(sorted(extra)))
    if kwargs.get("text") is not True or kwargs.get("capture_output") is not True:
        raise BoundChildDenied("TEXT_CAPTURE_REQUIRED")
    if kwargs.get("check") not in (None, False):
        raise BoundChildDenied("CHECK_MODE_NOT_SUPPORTED")
    if kwargs.get("shell", False):
        raise BoundChildDenied("SHELL_FORBIDDEN")
    profile = SUPPORTED[key]
    return argv, kwargs, key, profile


def _timeout(kwargs: Mapping[str, Any], maximum: int) -> float:
    raw = kwargs.get("timeout")
    if raw is None:
        raise BoundChildDenied("TIMEOUT_REQUIRED")
    try:
        value = float(raw)
    except Exception as exc:
        raise BoundChildDenied("TIMEOUT_INVALID") from exc
    if not 0 < value <= maximum:
        raise BoundChildDenied("TIMEOUT_OUT_OF_RANGE")
    return value


def _system_python(raw: str) -> str:
    expected = pathlib.Path(os.path.realpath(os.sys.executable))
    got = pathlib.Path(os.path.realpath(raw))
    if got != expected:
        raise BoundChildDenied("PYTHON_EXECUTABLE_NOT_CURRENT_INTERPRETER")
    # The parent may itself run from a venv or carrier-specific Python path that
    # is intentionally not mounted into the zero-ambient child. Authenticate
    # the caller against sys.executable, then use the verified namespace Python.
    inner = pathlib.Path("/usr/bin/python3")
    if not inner.is_file():
        raise BoundChildDenied("NAMESPACE_PYTHON_UNAVAILABLE")
    return str(inner)


def _strict_copy_tree(src: pathlib.Path, dst: pathlib.Path) -> tuple[int, int]:
    if not src.is_dir():
        raise BoundChildDenied("STAGED_SOURCE_ROOT_MISSING")
    count = total = 0
    for item in sorted(src.rglob("*")):
        if item.is_symlink():
            raise BoundChildDenied("STAGED_SOURCE_SYMLINK_FORBIDDEN")
        if item.is_dir():
            continue
        if not item.is_file():
            raise BoundChildDenied("STAGED_SOURCE_NONREGULAR_FILE")
        rel = item.relative_to(src)
        raw = item.read_bytes()
        count += 1
        total += len(raw)
        if count > 160 or total > 3_000_000:
            raise BoundChildDenied("STAGED_SOURCE_LIMIT_EXCEEDED")
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    if count == 0:
        raise BoundChildDenied("STAGED_SOURCE_EMPTY")
    return count, total


def _policy(*, input_dir: pathlib.Path, inner: list[str], timeout: float, cwd: str = "/input") -> dict[str, Any]:
    spec = {
        "argv": inner,
        "cwd": cwd,
        "timeout": timeout,
        "env_add": {"PYTHONPATH": "/input"},
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return {
        "argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
        "input_dir": str(input_dir),
        "limits": {
            "pids": 48,
            "memory_mb": 2048,
            "cpu_seconds": max(1, min(int(math.ceil(timeout)) + 1, 300)),
            "wallclock_s": max(1, min(int(math.ceil(timeout)) + 5, 600)),
            "scratch_mb": 256,
            "max_file_mb": 64,
            "nofile": 128,
            "broker_max_bytes": 8_000_000,
        },
    }


def _prepare_repo_python(
    argv: list[str],
    kwargs: Mapping[str, Any],
    *,
    maximum_timeout: int,
) -> dict[str, Any]:
    if len(argv) != 2:
        raise BoundChildDenied("REPO_PYTHON_ARGV_SHAPE_INVALID")
    py = _system_python(argv[0])
    cwd = _path(kwargs.get("cwd"))
    if not cwd.is_dir():
        raise BoundChildDenied("REPO_ROOT_MISSING")
    target = _path(argv[1])
    rel = _inside(cwd, target)
    if not target.is_file() or target.suffix != ".py":
        raise BoundChildDenied("REPO_PYTHON_TARGET_INVALID")
    if kwargs.get("env") is not None:
        raise BoundChildDenied("CUSTOM_ENV_FORBIDDEN")
    timeout = _timeout(kwargs, maximum_timeout)
    return {
        "input_dir": cwd,
        "inner": [py, "/input/" + rel.as_posix()],
        "timeout": timeout,
        "cleanup_dir": None,
    }


def _prepare_codec_probe(argv: list[str], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if len(argv) != 4:
        raise BoundChildDenied("CODEC_PROBE_ARGV_SHAPE_INVALID")
    py = _system_python(argv[0])
    repo = _path(kwargs.get("cwd"))
    if not repo.is_dir():
        raise BoundChildDenied("REPO_ROOT_MISSING")
    helper = _path(argv[1])
    expected_helper = (repo / "canonical/runtime/python_codec_probe.py").resolve()
    if helper != expected_helper or not helper.is_file():
        raise BoundChildDenied("CODEC_PROBE_HELPER_NOT_EXACT")
    site = _path(argv[2])
    if not site.is_dir():
        raise BoundChildDenied("CODEC_PROBE_SITE_INVALID")
    if kwargs.get("env") is not None:
        raise BoundChildDenied("CUSTOM_ENV_FORBIDDEN")
    try:
        modules = json.loads(argv[3])
    except Exception as exc:
        raise BoundChildDenied("CODEC_PROBE_MODULE_JSON_INVALID") from exc
    if (
        not isinstance(modules, list)
        or len(modules) != 1
        or not isinstance(modules[0], str)
        or not modules[0]
        or len(modules[0]) > 256
    ):
        raise BoundChildDenied("CODEC_PROBE_MODULE_LIST_INVALID")
    timeout = _timeout(kwargs, 90)
    stage = pathlib.Path(tempfile.mkdtemp(prefix="brain-bound-child-codec-"))
    try:
        (stage / "python_codec_probe.py").write_bytes(helper.read_bytes())
        _strict_copy_tree(site, stage / "site")
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {
        "input_dir": stage,
        "inner": [
            py,
            "/input/python_codec_probe.py",
            "/input/site",
            json.dumps(modules, separators=(",", ":")),
        ],
        "timeout": timeout,
        "cleanup_dir": stage,
    }


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    argv, kwargs, key, profile = _argv(context)
    if profile == "REPO_PYTHON_VERIFICATION":
        prepared = _prepare_repo_python(argv, kwargs, maximum_timeout=180)
    elif profile == "REPO_PYTHON_TEST_AUDIT":
        prepared = _prepare_repo_python(argv, kwargs, maximum_timeout=600)
    elif profile == "PYTHON_SOURCE_CODEC_PROBE":
        prepared = _prepare_codec_probe(argv, kwargs)
    else:
        raise BoundChildDenied("PROFILE_UNREACHABLE")
    return {
        **prepared,
        "profile": profile,
        "callsite_key": key,
        "original_argv": argv,
        "kwargs": kwargs,
        "policy": _policy(
            input_dir=prepared["input_dir"],
            inner=prepared["inner"],
            timeout=prepared["timeout"],
        ),
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
    return subprocess.CompletedProcess(
        args=prepared["original_argv"],
        returncode=int(result["returncode"]),
        stdout=stdout_b.decode("utf-8", errors="replace"),
        stderr=stderr_b.decode("utf-8", errors="replace"),
    )


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> Any:
        prepared = _prepare(context)
        try:
            result = confined._run_confined_with_popen(prepared["policy"], popen_impl)
            return _completed(prepared, result)
        finally:
            cleanup = prepared.get("cleanup_dir")
            if cleanup:
                shutil.rmtree(str(cleanup), ignore_errors=True)

    return execute
