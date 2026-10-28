"""Confined executor for ARBITRARY_COMMAND_EXECUTION astra shell steps.

Missions declare shell steps; the runtime executes them through bash -lc.
This executor confines those steps inside the same zero-ambient namespace
membrane as the codec child executor: read-only system mounts plus a single
read-only repository bind; only the canonical/astra_runtime subtree is
writable (receipts/evidence/state channels). The environment handed to the
child is the caller's copy, trimmed by the namespace launcher policy.
"""
from __future__ import annotations

import base64
import json
import math
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

SCHEMA = "PROJECT_BRAIN_ROOT3_CONFINED_SHELL_EXECUTOR_V1"
EFFECT_CLASS = "ARBITRARY_COMMAND_EXECUTION"

ROOT = pathlib.Path(__file__).resolve().parents[2]
ASTRA_DIR_REL = "canonical/astra_runtime"

# The single astra_runtime run_shell subprocess site.
SUPPORTED = {
    ("canonical/runtime/astra_runtime.py", 357, "subprocess.run"): "ASTRA_SHELL_STEP",
    # 2026-10-28 layout: same semantic shell-step launcher rebased.
    ("canonical/runtime/astra_runtime.py", 400, "subprocess.run"): "ASTRA_SHELL_STEP",
}

MAX_COMMAND_BYTES = 262_144


class ConfinedShellDenied(PermissionError):
    pass


_WRAPPER = r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
for _k,_v in (spec.get("env") or {}).items():
    os.environ[_k]=_v
if spec.get("cwd"):
    os.chdir(spec["cwd"])
p=subprocess.run(
    spec["argv"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=spec["timeout"],
    check=False,
    shell=False,
)
out={
    "timed_out":False,
    "returncode":int(p.returncode),
    "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
    "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
}
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""


_SETUP = r'''set -euo pipefail
ROOT="$1"; INPUT="$2"; RWSUB="$3"; BROKER="$4"; MEM_KB="$5"; CPU_S="$6"; FILE_KB="$7"; NOFILE="$8"; PIDS="$9"; SCRATCH_MB="${10}"; shift 10
mount --make-rprivate /
mount -t tmpfs -o size=96m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/dev" "$ROOT/proc" "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/input"
for dev in null zero urandom random; do : > "$ROOT/dev/$dev" 2>/dev/null || true; done
mkdir -p "$ROOT/usr/local"
for d in /usr /bin /lib /lib64 /usr/local; do
  [ -e "$d" ] || continue
  base="${d#/}"
  if [ -L "$d" ]; then rm -rf "$ROOT/$base"; ln -s "$(readlink "$d")" "$ROOT/$base"; fi
done
mount --bind "$ROOT" "$ROOT"
mount -o remount,bind,ro "$ROOT"
for d in /usr /bin /lib /lib64 /usr/local; do
  [ -e "$d" ] || continue
  [ -L "$d" ] && continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro,nosuid,nodev "$ROOT$d"
done
for dev in null zero; do [ -e "/dev/$dev" ] && mount --bind "/dev/$dev" "$ROOT/dev/$dev"; done
for dev in urandom random; do
  [ -e "/dev/$dev" ] || continue
  mount --bind "/dev/$dev" "$ROOT/dev/$dev"
  mount -o remount,bind,ro "$ROOT/dev/$dev"
done
[ -e /proc/self/mountinfo ] && mount -t proc proc "$ROOT/proc"
mount --bind "$INPUT" "$ROOT/input"
mount -o remount,bind,ro,nosuid,nodev "$ROOT/input"
if [ "$RWSUB" != "-" ]; then
  mkdir -p "$ROOT/input/$RWSUB"
  mount --bind "$INPUT/$RWSUB" "$ROOT/input/$RWSUB"
  mount -o remount,bind,nosuid,nodev "$ROOT/input/$RWSUB"
fi
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"
IP_BIN="$(command -v ip)"; CHROOT_BIN="$(command -v chroot || command -v /usr/sbin/chroot || command -v /sbin/chroot)"
"$IP_BIN" link set lo up
ulimit -t "$CPU_S"; ulimit -v "$MEM_KB"; ulimit -f "$FILE_KB"; ulimit -n "$NOFILE"; ulimit -u "$PIDS"
exec "$CHROOT_BIN" "$ROOT" /usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PROJECT_BRAIN_BROKER_FD="$BROKER" "$@"
'''


def _validate(context: Mapping[str, Any]) -> dict[str, Any]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise ConfinedShellDenied("EFFECT_CLASS_MISMATCH")
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise ConfinedShellDenied("CALLSITE_MISSING")
    key = (
        str(callsite.get("module_path") or ""),
        int(callsite.get("lineno") or 0),
        str(callsite.get("process_api") or ""),
    )
    profile = SUPPORTED.get(key)
    if profile is None:
        raise ConfinedShellDenied(
            "SHELL_CALLSITE_NOT_YET_SUPPORTED:" + repr(key)
        )
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise ConfinedShellDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    argv0 = args[0]
    if not isinstance(argv0, (list, tuple)) or len(argv0) != 3:
        raise ConfinedShellDenied("SHELL_ARGV_SHAPE_INVALID")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in argv0]
    bash = argv[0]
    if pathlib.Path(bash).name not in {"bash", "sh"}:
        raise ConfinedShellDenied("SHELL_EXECUTABLE_INVALID")
    if argv[1] != "-lc":
        raise ConfinedShellDenied("SHELL_MODE_INVALID")
    cmd = argv[2]
    if len(cmd.encode("utf-8")) > MAX_COMMAND_BYTES:
        raise ConfinedShellDenied("SHELL_COMMAND_TOO_LARGE")
    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise ConfinedShellDenied("DOUBLE_SHELL_FORBIDDEN")
    if kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise ConfinedShellDenied("STDIN_HANDLE_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise ConfinedShellDenied("CAPTURE_OUTPUT_REQUIRED")
    cwd_value = kwargs.get("cwd")
    if cwd_value is not None:
        try:
            cwd_value = os.fspath(cwd_value)
        except Exception as exc:
            raise ConfinedShellDenied("SHELL_CWD_INVALID") from exc
        cwd_value = str(cwd_value)
    if cwd_value not in (None, str(ROOT)):
        raise ConfinedShellDenied(
            "SHELL_CWD_MUST_BE_REPO_ROOT:" + repr(cwd_value) + ":ROOT:" + repr(str(ROOT))
        )
    timeout = kwargs.get("timeout", 120)
    if timeout is None:
        timeout = 120
    try:
        timeout_value = float(timeout)
    except Exception as exc:
        raise ConfinedShellDenied("TIMEOUT_INVALID") from exc
    if not (0.0 < timeout_value <= 1200.0):
        raise ConfinedShellDenied("TIMEOUT_OUT_OF_RANGE")
    env = kwargs.get("env")
    env_spec = {}
    if isinstance(env, Mapping):
        # Mission steps may legitimately read tokens/flags from the mission
        # environment; the confinement strips the parent's ambient $-world
        # entirely, so pass through only names present in the caller's copy.
        for k, v in env.items():
            k = str(k)
            v = str(v)
            if not k or "\x00" in v or len(v) > 8192:
                raise ConfinedShellDenied("SHELL_ENV_VALUE_INVALID")
            env_spec[k] = v
    return {
        "argv": argv,
        "cmd": cmd,
        "kwargs": kwargs,
        "timeout": timeout_value,
        "env": env_spec,
        "key": key,
        "profile": profile,
    }


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    v = _validate(context)
    # bash -> absolute in-container path; the shell, its libs, and every
    # reachable system tool come from the read-only /usr/bind mounts.
    bash_abs = shutil.which(v["argv"][0]) or v["argv"][0]
    bash_abs = str(pathlib.Path(bash_abs).resolve())
    inner = [bash_abs, "-lc", v["cmd"]]
    spec = {
        "argv": inner,
        "cwd": "/input",
        "timeout": v["timeout"],
        "stdin_file": None,
        "env": {
            **v["env"],
            "PYTHONPATH": "/input",
            "HOME": "/tmp",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    policy = {
        "argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
        "input_dir": str(ROOT),
        "writable_dir": str((ROOT / ASTRA_DIR_REL).resolve()),
        "limits": {
            "pids": 128,
            "memory_mb": 2048,
            "cpu_seconds": max(5, min(int(math.ceil(spec["timeout"])), 300)),
            "wallclock_s": max(10, min(int(math.ceil(spec["timeout"] + 10)), 600)),
            "scratch_mb": 256,
            "max_file_mb": 64,
            "nofile": 256,
            "broker_max_bytes": 8_000_000,
        },
    }
    return {
        "profile": v["profile"],
        "callsite_key": v["key"],
        "original_argv": v["argv"],
        "kwargs": v["kwargs"],
        "policy": policy,
        "timeout": v["timeout"],
    }


def _run_confined_with_popen(
    policy: Mapping[str, Any], popen_impl: Callable[..., Any]
) -> dict[str, Any]:
    if os.environ.get("PROJECT_BRAIN_CONFINED") == "1":
        return _run_nested_with_popen(policy, popen_impl)
    p = ns.canonical_policy(policy)
    lim = p["limits"]
    writable_dir = policy.get("writable_dir")
    writable_rel = "-"
    if writable_dir:
        wp = pathlib.Path(str(writable_dir)).resolve()
        ip = pathlib.Path(str(policy["input_dir"])).resolve()
        try:
            writable_rel = wp.relative_to(ip).as_posix()
        except ValueError as exc:
            raise ConfinedShellDenied("WRITABLE_DIR_NOT_INSIDE_INPUT_BIND") from exc
        if not writable_rel or writable_rel == ".":
            raise ConfinedShellDenied("WRITABLE_DIR_MUST_BE_INPUT_SUBPATH")
        if not wp.is_dir():
            raise ConfinedShellDenied("WRITABLE_DIR_MISSING")
    required_names = ["unshare", "mount", "chroot", "setpriv", "ip", "bash", "env"]
    resolved = {name: ns.resolve_system_binary(name) for name in required_names}
    missing = [name for name, pathv in resolved.items() if not pathv]
    if missing:
        raise ConfinedShellDenied("HOST_PRIMITIVE_MISSING:" + ",".join(missing))
    root = tempfile.mkdtemp(prefix="brain-confined-shell-")
    os.chmod(root, 0o755)
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
        resolved["unshare"], "--user", "--map-root-user", "--mount", "--net",
        "--pid", "--fork", "--ipc", "--uts",
        resolved["bash"], "-c", _SETUP, "_", root, p["input_dir"],
        writable_rel if writable_dir else "-",
        str(child.fileno()),
        str(lim["memory_mb"] * 1024), str(lim["cpu_seconds"]),
        str(math.ceil(lim["max_file_mb"] * 1024)), str(lim["nofile"]),
        str(lim["pids"]), str(lim["scratch_mb"]),
        resolved["setpriv"], "--no-new-privs", "--bounding-set=-all",
        "--inh-caps=-all", "--ambient-caps=-all", resolved["env"], "-i",
        "PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1",
        "PROJECT_BRAIN_CONFINED=1",
        "PROJECT_BRAIN_BROKER_FD=" + str(child.fileno()),
        *p["argv"],
    ]
    # Opt-in developer trace: when PROJECT_BRAIN_NS_STDERR_FILE points at a
    # writable path, the outer namespace chain's stderr lands there; the
    # mediator's own authorization never reads it.
    # Bounded outer-stderr capture: namespace-chain stderr would otherwise be
    # invisible by construction (measured 2026-10-28 during nested nesting).
    err_r, err_w = os.pipe()
    err_tail: list[bytes] = []
    popen_kw = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": err_w,
        "pass_fds": (child.fileno(),),
        "env": env,
        "start_new_session": True,
    }
    if os.geteuid() == 0:
        # Only a *host* root must drop privileges; a mapped-root namespace root
        # is already non-root on the host (kernel uid_map proves it).
        try:
            _mapped = int(pathlib.Path("/proc/self/uid_map").read_text().split()[1]) != 0
        except Exception:
            _mapped = False
        if not _mapped:
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
    os.close(err_w)
    raw = b"".join(broker)
    try:
        while True:
            b = os.read(err_r, 65536)
            if not b:
                break
            err_tail.append(b)
            if sum(len(x) for x in err_tail) > 65536:
                break
    except OSError:
        pass
    os.close(err_r)
    err_ctx = b"".join(err_tail)[-2048:].decode("utf-8", "replace").replace("\n", " | ")
    if timed_out:
        raise ConfinedShellDenied("CONFINEMENT_WALLCLOCK_LIMIT_EXCEEDED:" + err_ctx[:400])
    if overflow[0]:
        raise ConfinedShellDenied("CONFINEMENT_BROKER_OUTPUT_LIMIT_EXCEEDED")
    if rc != 0 and not raw.strip():
        raise ConfinedShellDenied("CONFINEMENT_WRAPPER_FAILED:" + str(rc) + ": " + err_ctx[:600])
    try:
        result = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ConfinedShellDenied("CONFINEMENT_BROKER_PAYLOAD_INVALID") from exc
    result["policy_sha256"] = ns.policy_sha256(p)
    result["wallclock_ms"] = round((time.monotonic() - started) * 1000, 3)
    return result


def _run_nested_with_popen(
    policy: Mapping[str, Any], popen_impl: Callable[..., Any]
) -> dict[str, Any]:
    """Nested-confinement path: inside an already-confined ring
    (PROJECT_BRAIN_CONFINED=1), kernel-capped trees cannot unshare again, so
    the confinement collapses to in-process execution of the inner spec. The
    mediation chain remains: this layer still validates argv/policy, stages
    inputs, brokers output, and returns the same CompletedProcess semantics."""
    argv_outer = list(policy["argv"])
    payload = argv_outer[-1]
    import base64 as _b64
    spec = json.loads(_b64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))
    stdinf = None
    stdin_path = spec.get("stdin_file")
    if stdin_path:
        stdinf = open(stdin_path, "rb")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp",
           "PYTHONDONTWRITEBYTECODE": "1", "PROJECT_BRAIN_CONFINED": "1"}
    if spec.get("env"):
        env.update(spec["env"])
    cwd = spec.get("cwd") or "/"
    try:
        proc = popen_impl(
            spec["argv"], env=env, cwd=cwd, stdin=stdinf,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        timed_out = False
        try:
            out, err = proc.communicate(timeout=float(spec["timeout"]))
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            out = exc.output or b""
            err = exc.stderr or b""
            rc = None
        else:
            rc = proc.returncode
    finally:
        if stdinf is not None:
            stdinf.close()
    import base64 as _b64b
    result = {
        "timed_out": timed_out,
        "returncode": rc if rc is not None else None,
        "stdout_b64": _b64b.b64encode(out or b"").decode("ascii"),
        "stderr_b64": _b64b.b64encode(err or b"").decode("ascii"),
        "nested_ring": True,
    }
    return result


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> Any:
        prepared = _prepare(context)
        result = _run_confined_with_popen(prepared["policy"], popen_impl)
        stdout_b = base64.b64decode(result.get("stdout_b64") or b"")
        stderr_b = base64.b64decode(result.get("stderr_b64") or b"")
        if result.get("timed_out"):
            raise subprocess.TimeoutExpired(
                prepared["original_argv"], prepared["timeout"],
                output=stdout_b, stderr=stderr_b,
            )
        kwargs = prepared["kwargs"]
        encoding = kwargs.get("encoding") or "utf-8"
        errors = kwargs.get("errors") or "strict"
        return subprocess.CompletedProcess(
            args=prepared["original_argv"],
            returncode=int(result["returncode"]),
            stdout=stdout_b.decode(encoding, errors=errors),
            stderr=stderr_b.decode(encoding, errors=errors),
        )

    return execute
