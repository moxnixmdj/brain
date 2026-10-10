from __future__ import annotations

import base64
import io
import json
import math
import os
import pathlib
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_LOCAL_FILE_QUERY_EXECUTOR_V1"
EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"

SUPPORTED = {
    ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py", 32, "subprocess.run"): "TAR_LIST",
    ("canonical/runtime/bound_capabilities/jq_query.py", 41, "subprocess.run"): "JQ",
    ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 44, "subprocess.run"): "TESSERACT_STDOUT",
    ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py", 66, "subprocess.run"): "SQLITE_READ",
    ("canonical/runtime/bound_capabilities/yq_yaml_json.py", 21, "subprocess.run"): "YQ",
}

JQ_FORBIDDEN = (
    r"(?<![A-Za-z0-9_.])import\s+",
    r"(?<![A-Za-z0-9_.])include\s+",
    r"(?<![A-Za-z0-9_.])module\s+",
    r"(?<![A-Za-z0-9_.])input\s*\(",
    r"(?<![A-Za-z0-9_.])inputs\b",
    r"(?<![A-Za-z0-9_])env\.",
    r"\$ENV\b",
)

_WRAPPER = r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
if spec.get("cwd"):
    os.chdir(spec["cwd"])
try:
    p=subprocess.run(
        spec["argv"],
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=spec["timeout"],
        check=False,
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


class ReadOnlyQueryDenied(PermissionError):
    pass


def _path(value: Any) -> pathlib.Path:
    try:
        return pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc:
        raise ReadOnlyQueryDenied("PATH_INVALID") from exc


def _inside(root: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    try:
        return target.relative_to(root)
    except ValueError as exc:
        raise ReadOnlyQueryDenied("INPUT_PATH_OUTSIDE_DECLARED_ROOT") from exc


def _resolve_executable(raw: Any, expected: set[str]) -> str:
    token = str(raw)
    base = pathlib.Path(token).name
    if base not in expected:
        raise ReadOnlyQueryDenied("EXECUTABLE_NOT_ALLOWED:" + base)
    resolved = token if os.path.isabs(token) else shutil.which(token)
    if not resolved:
        raise ReadOnlyQueryDenied("EXECUTABLE_UNAVAILABLE:" + base)
    p = pathlib.Path(resolved).resolve()
    if not (str(p).startswith("/usr/") or str(p).startswith("/bin/")):
        raise ReadOnlyQueryDenied("EXECUTABLE_PATH_NOT_SYSTEM:" + str(p))
    return str(p)


def _timeout(kwargs: Mapping[str, Any], maximum: int = 180) -> float:
    raw = kwargs.get("timeout", 60)
    if raw is None:
        raw = 60
    try:
        value = float(raw)
    except Exception as exc:
        raise ReadOnlyQueryDenied("TIMEOUT_INVALID") from exc
    if not (0 < value <= maximum):
        raise ReadOnlyQueryDenied("TIMEOUT_OUT_OF_RANGE")
    return value


def _validate_common(context: Mapping[str, Any]) -> tuple[list[str], dict[str, Any], tuple[str, int, str], str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise ReadOnlyQueryDenied("EFFECT_CLASS_MISMATCH")
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise ReadOnlyQueryDenied("CALLSITE_MISSING")
    key = (
        str(callsite.get("module_path") or ""),
        int(callsite.get("lineno") or 0),
        str(callsite.get("process_api") or ""),
    )
    profile = SUPPORTED.get(key)
    if profile is None:
        raise ReadOnlyQueryDenied("READ_ONLY_QUERY_CALLSITE_NOT_YET_SUPPORTED:" + repr(key))
    if key[2] != "subprocess.run":
        raise ReadOnlyQueryDenied("PROCESS_API_NOT_SUPPORTED")
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise ReadOnlyQueryDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (list, tuple)) or not command:
        raise ReadOnlyQueryDenied("COMMAND_ARGV_REQUIRED")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise ReadOnlyQueryDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None:
        raise ReadOnlyQueryDenied("CUSTOM_ENV_FORBIDDEN")
    if kwargs.get("input") is not None or kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise ReadOnlyQueryDenied("STDIN_OR_INPUT_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise ReadOnlyQueryDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True or kwargs.get("encoding")):
        raise ReadOnlyQueryDenied("TEXT_MODE_REQUIRED")
    return argv, kwargs, key, profile


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    argv, kwargs, key, profile = _validate_common(context)
    cwd_raw = kwargs.get("cwd")
    cwd = _path(cwd_raw) if cwd_raw is not None else None

    if profile == "TAR_LIST":
        if len(argv) != 3 or argv[1] != "-tzf":
            raise ReadOnlyQueryDenied("TAR_LIST_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"tar"})
        src = _path(argv[2])
        if not src.is_file():
            raise ReadOnlyQueryDenied("TAR_INPUT_MISSING")
        input_dir = src.parent
        inner = [exe, "-tzf", "/input/" + src.name]
        inner_cwd = "/input"

    elif profile == "JQ":
        exe = _resolve_executable(argv[0], {"jq"})
        offset = 1
        raw_flag = False
        if len(argv) >= 2 and argv[1] == "-r":
            raw_flag = True
            offset = 2
        if len(argv) != offset + 2:
            raise ReadOnlyQueryDenied("JQ_SHAPE_INVALID")
        filt = argv[offset]
        if not filt or len(filt) > 8000 or any(re.search(p, filt, flags=re.I) for p in JQ_FORBIDDEN):
            raise ReadOnlyQueryDenied("JQ_FILTER_FORBIDDEN")
        src = _path(argv[offset + 1])
        root = cwd or src.parent
        if not root.is_dir() or not src.is_file():
            raise ReadOnlyQueryDenied("JQ_INPUT_INVALID")
        rel = _inside(root, src)
        input_dir = root
        inner = [exe] + (["-r"] if raw_flag else []) + [filt, "/input/" + rel.as_posix()]
        inner_cwd = "/input"

    elif profile == "YQ":
        if len(argv) != 3 or argv[1] != ".":
            raise ReadOnlyQueryDenied("YQ_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"yq"})
        src = _path(argv[2])
        root = cwd or src.parent
        if not root.is_dir() or not src.is_file():
            raise ReadOnlyQueryDenied("YQ_INPUT_INVALID")
        rel = _inside(root, src)
        input_dir = root
        inner = [exe, ".", "/input/" + rel.as_posix()]
        inner_cwd = "/input"

    elif profile == "SQLITE_READ":
        if len(argv) != 4 or argv[1] != "-json":
            raise ReadOnlyQueryDenied("SQLITE_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"sqlite3"})
        db = _path(argv[2])
        if not db.is_file():
            raise ReadOnlyQueryDenied("SQLITE_DB_MISSING")
        sql = argv[3].strip()
        allowed = (
            re.match(r"(?is)^SELECT\s+", sql)
            or re.fullmatch(r'(?is)PRAGMA\s+table_info\("[A-Za-z_][A-Za-z0-9_]{0,127}"\)', sql)
            or re.fullmatch(r"(?is)PRAGMA\s+integrity_check", sql)
        )
        if not allowed:
            raise ReadOnlyQueryDenied("SQLITE_MUTATING_OR_UNKNOWN_SQL_FORBIDDEN")
        input_dir = db.parent
        inner = [exe, "-json", "/input/" + db.name, sql]
        inner_cwd = "/input"

    elif profile == "TESSERACT_STDOUT":
        if len(argv) != 7 or argv[2] != "stdout" or argv[3] != "-l" or argv[5] != "--psm":
            raise ReadOnlyQueryDenied("TESSERACT_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"tesseract"})
        src = _path(argv[1])
        lang = argv[4]
        psm = argv[6]
        if not src.is_file() or not lang.replace("+", "").isalnum() or psm not in {"3", "6", "7", "11"}:
            raise ReadOnlyQueryDenied("TESSERACT_INPUT_OR_OPTIONS_INVALID")
        input_dir = src.parent
        inner = [exe, "/input/" + src.name, "stdout", "-l", lang, "--psm", psm]
        inner_cwd = "/input"

    else:
        raise ReadOnlyQueryDenied("PROFILE_UNREACHABLE")

    timeout = _timeout(kwargs)
    spec = {"argv": inner, "cwd": inner_cwd, "timeout": timeout}
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    policy = {
        "argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
        "input_dir": str(input_dir),
        "limits": {
            "pids": 32,
            "memory_mb": 1024,
            "cpu_seconds": max(1, min(int(math.ceil(timeout)), 300)),
            "wallclock_s": max(1, min(int(math.ceil(timeout + 5)), 600)),
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
    }


def _run_confined_with_popen(policy: Mapping[str, Any], popen_impl: Callable[..., Any]) -> dict[str, Any]:
    p = ns.canonical_policy(policy)
    lim = p["limits"]
    required_names = ["unshare", "mount", "chroot", "setpriv", "ip", "bash", "env"]
    resolved = {name: shutil.which(name) for name in required_names}
    missing = [name for name, path in resolved.items() if not path]
    if missing:
        raise ReadOnlyQueryDenied("HOST_PRIMITIVE_MISSING:" + ",".join(missing))
    root = tempfile.mkdtemp(prefix="brain-ro-query-")
    os.chown(root, p["host_uid"], p["host_gid"])
    parent, child = socket.socketpair()
    broker: list[bytes] = []
    overflow = [False]

    def reader() -> None:
        total = 0
        try:
            while True:
                b = parent.recv(65536)
                if not b:
                    break
                total += len(b)
                if total > lim["broker_max_bytes"]:
                    overflow[0] = True
                    try:
                        parent.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    break
                broker.append(b)
        except OSError:
            pass

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    env = {"BROKER_FD": str(child.fileno()), "PYTHONDONTWRITEBYTECODE": "1"}
    cmd = [
        resolved["unshare"], "--user", "--map-root-user", "--mount", "--net", "--pid", "--fork", "--ipc", "--uts",
        resolved["bash"], "-c", ns._SETUP, "_", root, p["input_dir"], str(child.fileno()),
        str(lim["memory_mb"] * 1024), str(lim["cpu_seconds"]),
        str(math.ceil(lim["max_file_mb"] * 1024)), str(lim["nofile"]), str(lim["pids"]),
        str(lim["scratch_mb"]), resolved["setpriv"], "--no-new-privs", "--bounding-set=-all",
        "--inh-caps=-all", "--ambient-caps=-all", resolved["env"], "-i", "PATH=/usr/bin:/bin",
        "HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1", "PROJECT_BRAIN_BROKER_FD=" + str(child.fileno()),
        *p["argv"],
    ]
    popen_kw = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "pass_fds": (child.fileno(),),
        "env": env,
        "start_new_session": True,
    }
    if os.geteuid() == 0:
        popen_kw.update(user=p["host_uid"], group=p["host_gid"], extra_groups=[])
    started = time.monotonic()
    timed_out = False
    try:
        proc = popen_impl(cmd, **popen_kw)
        child.close()
        try:
            rc = proc.wait(timeout=lim["wallclock_s"])
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, 9)
            except ProcessLookupError:
                pass
            rc = proc.wait(timeout=5)
        th.join(timeout=2)
    finally:
        try:
            child.close()
        except OSError:
            pass
        try:
            parent.close()
        except OSError:
            pass
        shutil.rmtree(root, ignore_errors=True)
    raw = b"".join(broker)
    if timed_out:
        raise ReadOnlyQueryDenied("CONFINEMENT_WALLCLOCK_LIMIT_EXCEEDED")
    if overflow[0]:
        raise ReadOnlyQueryDenied("CONFINEMENT_BROKER_OUTPUT_LIMIT_EXCEEDED")
    if rc != 0:
        raise ReadOnlyQueryDenied("CONFINEMENT_WRAPPER_FAILED:" + str(rc))
    try:
        result = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ReadOnlyQueryDenied("CONFINEMENT_BROKER_PAYLOAD_INVALID") from exc
    result["policy_sha256"] = ns.policy_sha256(p)
    result["wallclock_ms"] = round((time.monotonic() - started) * 1000, 3)
    return result


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> Any:
        prepared = _prepare(context)
        result = _run_confined_with_popen(prepared["policy"], popen_impl)
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
        return subprocess.CompletedProcess(
            args=prepared["original_argv"],
            returncode=int(result["returncode"]),
            stdout=stdout,
            stderr=stderr,
        )

    return execute
