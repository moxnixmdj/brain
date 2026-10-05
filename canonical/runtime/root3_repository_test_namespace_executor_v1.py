from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as ro

SCHEMA = "PROJECT_BRAIN_ROOT3_REPOSITORY_TEST_NAMESPACE_EXECUTOR_V1"
EFFECT_CLASS = "BOUND_CHILD_CODE_EXECUTION"

SUPPORTED = {
    ("canonical/runtime/astra_runtime.py", 1215, "subprocess.run"): "REPOSITORY_TEST_EXECUTION",
    ("canonical/runtime/bound_capabilities/python_test_audit.py", 50, "subprocess.run"): "REPOSITORY_TEST_EXECUTION",
}

_RUNNER = r"""
import pathlib,sys,types
snapshot=pathlib.Path(sys.argv[1])
logical=sys.argv[2]
raw=snapshot.read_bytes()
sys.argv=[logical]
script_dir=str(pathlib.PurePosixPath(logical).parent)
sys.path=[script_dir,"/input"]+[p for p in sys.path if p not in (script_dir,"/input","")]
module=types.ModuleType("__main__")
module.__file__=logical
module.__package__=None
module.__cached__=None
sys.modules["__main__"]=module
exec(compile(raw,logical,"exec"),module.__dict__,module.__dict__)
"""

_WRAPPER = r"""
import base64,hashlib,json,os,pathlib,subprocess,sys,traceback
broker_fd=int(os.environ.get("PROJECT_BRAIN_BROKER_FD","-1"))
try:
    spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
    if broker_fd<0:
        raise RuntimeError("BROKER_FD_MISSING")
    os.environ.pop("PROJECT_BRAIN_BROKER_FD",None)
    os.set_inheritable(broker_fd,False)
    src=pathlib.Path(spec["source_path"])
    raw=src.read_bytes()
    observed=hashlib.sha256(raw).hexdigest()
    if observed!=spec["test_sha256"]:
        out={
          "wrapper_error":None,
          "binding_error":"TEST_PROGRAM_SHA256_MISMATCH",
          "timed_out":False,
          "returncode":None,
          "stdout_b64":"",
          "stderr_b64":"",
          "test_sha256_observed":observed,
        }
    else:
        snap=pathlib.Path("/work/test_snapshot.py")
        snap.write_bytes(raw)
        nested_env={
          "PATH":"/usr/bin:/bin",
          "HOME":"/tmp",
          "PYTHONDONTWRITEBYTECODE":"1",
        }
        try:
            p=subprocess.run(
                [spec["python"],"-I","-c",spec["runner"],str(snap),spec["logical_path"]],
                cwd=spec["cwd"],
                env=nested_env,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=spec["timeout"],
                check=False,
                close_fds=True,
            )
            out={
              "wrapper_error":None,
              "binding_error":None,
              "timed_out":False,
              "returncode":int(p.returncode),
              "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
              "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
              "test_sha256_observed":observed,
            }
        except subprocess.TimeoutExpired as exc:
            out={
              "wrapper_error":None,
              "binding_error":None,
              "timed_out":True,
              "returncode":None,
              "stdout_b64":base64.b64encode(exc.output or b"").decode("ascii"),
              "stderr_b64":base64.b64encode(exc.stderr or b"").decode("ascii"),
              "test_sha256_observed":observed,
            }
except Exception as exc:
    out={
      "wrapper_error":type(exc).__name__+":"+str(exc),
      "binding_error":None,
      "timed_out":False,
      "returncode":None,
      "stdout_b64":"",
      "stderr_b64":base64.b64encode(traceback.format_exc().encode("utf-8")).decode("ascii"),
      "test_sha256_observed":None,
    }
if broker_fd>=0:
    os.write(broker_fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""


class RepositoryTestDenied(PermissionError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _callsite(context: Mapping[str, Any]) -> tuple[str, int, str]:
    raw = context.get("callsite")
    if not isinstance(raw, Mapping):
        raise RepositoryTestDenied("CALLSITE_MISSING")
    return (
        str(raw.get("module_path") or ""),
        int(raw.get("lineno") or 0),
        str(raw.get("process_api") or ""),
    )


def _system_python(raw: Any) -> str:
    token = os.fspath(raw) if isinstance(raw, os.PathLike) else str(raw)
    resolved = token if os.path.isabs(token) else shutil.which(token)
    if not resolved:
        raise RepositoryTestDenied("PYTHON_EXECUTABLE_UNAVAILABLE")
    p = pathlib.Path(resolved).resolve()
    if not (str(p).startswith("/usr/") or str(p).startswith("/bin/")):
        raise RepositoryTestDenied("PYTHON_EXECUTABLE_NOT_SYSTEM:" + str(p))
    if "python" not in p.name.lower():
        raise RepositoryTestDenied("EXECUTABLE_NOT_PYTHON:" + p.name)
    return str(p)


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise RepositoryTestDenied("EFFECT_CLASS_MISMATCH")
    site = _callsite(context)
    if site not in SUPPORTED:
        raise RepositoryTestDenied("REPOSITORY_TEST_CALLSITE_NOT_SUPPORTED:" + repr(site))
    if context.get("api") != "subprocess.run":
        raise RepositoryTestDenied("PROCESS_API_NOT_SUPPORTED")

    args = context.get("args")
    if not isinstance(args, (tuple, list)) or len(args) != 1:
        raise RepositoryTestDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (tuple, list)) or len(command) != 2:
        raise RepositoryTestDenied("EXACT_PYTHON_TEST_ARGV_REQUIRED")

    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise RepositoryTestDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None or kwargs.get("input") is not None:
        raise RepositoryTestDenied("CUSTOM_ENV_OR_INPUT_FORBIDDEN")
    if kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise RepositoryTestDenied("STDIN_FORBIDDEN")
    if kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
        raise RepositoryTestDenied("EXPLICIT_STDOUT_STDERR_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise RepositoryTestDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True):
        raise RepositoryTestDenied("TEXT_MODE_REQUIRED")
    if kwargs.get("check") not in (None, False):
        raise RepositoryTestDenied("CHECK_MODE_NOT_SUPPORTED")

    cwd_raw = kwargs.get("cwd")
    if cwd_raw is None:
        raise RepositoryTestDenied("REPOSITORY_CWD_REQUIRED")
    repo = pathlib.Path(os.fspath(cwd_raw)).resolve()
    if not repo.is_dir():
        raise RepositoryTestDenied("REPOSITORY_CWD_MISSING")

    python = _system_python(command[0])
    test_file = pathlib.Path(os.fspath(command[1])).resolve()
    try:
        rel = test_file.relative_to(repo)
    except ValueError as exc:
        raise RepositoryTestDenied("TEST_PROGRAM_OUTSIDE_REPOSITORY") from exc
    if not test_file.is_file() or test_file.is_symlink() or test_file.suffix != ".py":
        raise RepositoryTestDenied("TEST_PROGRAM_NOT_REGULAR_PYTHON_FILE")
    if any(part in ("", ".", "..") for part in rel.parts):
        raise RepositoryTestDenied("TEST_PROGRAM_RELATIVE_PATH_INVALID")

    try:
        timeout = float(kwargs.get("timeout"))
    except Exception as exc:
        raise RepositoryTestDenied("TIMEOUT_INVALID") from exc
    if not (0 < timeout <= 600):
        raise RepositoryTestDenied("TIMEOUT_OUT_OF_RANGE")

    raw = test_file.read_bytes()
    test_sha = _sha256(raw)
    logical = "/input/" + rel.as_posix()
    spec = {
        "python": python,
        "source_path": logical,
        "logical_path": logical,
        "cwd": "/input",
        "timeout": timeout,
        "test_sha256": test_sha,
        "runner": _RUNNER,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    policy = {
        "argv": [python, "-I", "-c", _WRAPPER, encoded],
        "input_dir": str(repo),
        "limits": {
            "pids": 64,
            "memory_mb": 2048,
            "cpu_seconds": max(1, min(int(timeout), 300)),
            "wallclock_s": max(1, min(int(timeout) + 10, 600)),
            "scratch_mb": 128,
            "max_file_mb": 32,
            "nofile": 128,
            "broker_max_bytes": 8_000_000,
        },
    }
    return {
        "site": site,
        "profile": SUPPORTED[site],
        "repo": str(repo),
        "test_path": str(test_file),
        "test_relative_path": rel.as_posix(),
        "test_sha256": test_sha,
        "original_argv": [os.fspath(command[0]), os.fspath(command[1])],
        "kwargs": kwargs,
        "timeout": timeout,
        "policy": policy,
    }


def _decode_result(result: Mapping[str, Any], prepared: Mapping[str, Any]) -> subprocess.CompletedProcess:
    if result.get("wrapper_error"):
        raise RepositoryTestDenied("WRAPPER_ERROR:" + str(result["wrapper_error"]))
    if result.get("binding_error"):
        raise RepositoryTestDenied(str(result["binding_error"]))
    if result.get("test_sha256_observed") != prepared["test_sha256"]:
        raise RepositoryTestDenied("TEST_PROGRAM_SHA256_POSTCHECK_MISMATCH")
    try:
        stdout_b = base64.b64decode(result.get("stdout_b64") or "", validate=True)
        stderr_b = base64.b64decode(result.get("stderr_b64") or "", validate=True)
    except Exception as exc:
        raise RepositoryTestDenied("BROKER_CAPTURE_INVALID") from exc
    if result.get("timed_out") is True:
        raise subprocess.TimeoutExpired(
            prepared["original_argv"],
            prepared["timeout"],
            output=stdout_b,
            stderr=stderr_b,
        )
    rc = result.get("returncode")
    if not isinstance(rc, int) or isinstance(rc, bool):
        raise RepositoryTestDenied("RETURN_CODE_INVALID")
    encoding = prepared["kwargs"].get("encoding") or "utf-8"
    errors = prepared["kwargs"].get("errors") or "strict"
    cp = subprocess.CompletedProcess(
        args=prepared["original_argv"],
        returncode=rc,
        stdout=stdout_b.decode(encoding, errors=errors),
        stderr=stderr_b.decode(encoding, errors=errors),
    )
    cp.project_brain_execution_receipt = {
        "schema": SCHEMA,
        "profile": prepared["profile"],
        "callsite": list(prepared["site"]),
        "test_relative_path": prepared["test_relative_path"],
        "test_sha256": prepared["test_sha256"],
        "namespace_policy_sha256": result.get("policy_sha256"),
        "material_effects_committed": 0,
        "repository_read_only": True,
        "test_child_broker_fd_inherited": False,
    }
    return cp


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> Any:
        prepared = _prepare(context)
        result = ro._run_confined_with_popen(prepared["policy"], popen_impl)
        return _decode_result(result, prepared)

    return execute
