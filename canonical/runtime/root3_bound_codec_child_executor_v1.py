"""Confined executor for BOUND_CHILD_CODE_EXECUTION codec probes.

Executes the two codec-probe call sites that carry the effect class
BOUND_CHILD_CODE_EXECUTION under the Root3 process membrane:
 - auto_npm_library_acquisition._probe_contract (node codec contract probe)

The child runs inside the same zero-ambient namespace membrane as the
read-only/temp executors: read-only host system, one read-only input bind,
private writable /tmp+work, no privilege escalation, one broker output fd.
The input bind is a freshly staged probe directory containing exactly the
files the probe declares: the copied codec runner, the extracted package
tree, and the probe fixture/stdin payloads. Nothing else enters the
confinement and no other path is reachable.
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

SCHEMA = "PROJECT_BRAIN_ROOT3_BOUND_CODEC_CHILD_EXECUTOR_V1"
EFFECT_CLASS = "BOUND_CHILD_CODE_EXECUTION"

NPM_PROBE_SITE = (
    "canonical/runtime/auto_npm_library_acquisition.py",
    255,
    "subprocess.run",
)
SRC_CODEC_PROBE_SITE = (
    "canonical/runtime/auto_python_source_codec_acquisition.py",
    307,
    "subprocess.run",
)
SRC_CODEC_PRIME_PROBE_SITE = (
    "canonical/runtime/auto_python_source_codec_acquisition.py",
    184,
    "subprocess.run",
)

VERIFY_MISSION_SITE = (
    "canonical/runtime/astra_runtime.py",
    6405,
    "subprocess.run",
)
VERIFY_MISSION_SITE_LEGACY_20261028 = (
    "canonical/runtime/astra_runtime.py",
    6306,
    "subprocess.run",
)

NODE_LIBRARY_RUN_SITE = (
    "canonical/runtime/bound_capabilities/node_library_codec.py",
    16,
    "subprocess.run",
)
PY_SOURCE_TREE_RUN_SITE = (
    "canonical/runtime/bound_capabilities/python_source_tree_codec.py",
    48,
    "subprocess.run",
)

SUPPORTED = {
    NPM_PROBE_SITE: "NPM_CODEC_CONTRACT_PROBE",
    SRC_CODEC_PROBE_SITE: "PY_SOURCE_CODEC_CONTRACT_PROBE",
    SRC_CODEC_PRIME_PROBE_SITE: "PY_SOURCE_CODEC_CONTRACT_PROBE",
    VERIFY_MISSION_SITE: "ASTRA_VERIFICATION_MISSION_CHILD",
    VERIFY_MISSION_SITE_LEGACY_20261028: "ASTRA_VERIFICATION_MISSION_CHILD",
    # Production codec invocations from VERIFIED registry bindings: same
    # confinement machinery as the contract probes, plus a writable stage and
    # a post-run output handoff for encoder artifacts.
    NODE_LIBRARY_RUN_SITE: "NODE_LIBRARY_CODEC_RUN",
    PY_SOURCE_TREE_RUN_SITE: "PY_SOURCE_TREE_CODEC_RUN",
}

ROOT = pathlib.Path(__file__).resolve().parents[2]
NODE_RUNNER_REL = "canonical/runtime/node_codec_runner.js"
LAUNCHER_REL = "canonical/runtime/root3_production_astra_launcher_v1.py"
ASTRA_DIR_REL = "canonical/astra_runtime"
MAX_INPUT_BYTES = 1_048_576


class BoundCodecChildDenied(PermissionError):
    pass


def _path(value: Any) -> pathlib.Path:
    try:
        return pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc:
        raise BoundCodecChildDenied("PATH_INVALID") from exc


def _validate_common(
    context: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any], tuple[str, int, str], str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise BoundCodecChildDenied("EFFECT_CLASS_MISMATCH")
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise BoundCodecChildDenied("CALLSITE_MISSING")
    key = (
        str(callsite.get("module_path") or ""),
        int(callsite.get("lineno") or 0),
        str(callsite.get("process_api") or ""),
    )
    profile = SUPPORTED.get(key)
    if profile is None:
        raise BoundCodecChildDenied(
            "BOUND_CODEC_CHILD_CALLSITE_NOT_YET_SUPPORTED:" + repr(key)
        )
    if key[2] != "subprocess.run":
        raise BoundCodecChildDenied("PROCESS_API_NOT_SUPPORTED")
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise BoundCodecChildDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (list, tuple)) or not command:
        raise BoundCodecChildDenied("COMMAND_ARGV_REQUIRED")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise BoundCodecChildDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None and profile != "ASTRA_VERIFICATION_MISSION_CHILD":
        raise BoundCodecChildDenied("CUSTOM_ENV_FORBIDDEN")
    if kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise BoundCodecChildDenied("STDIN_HANDLE_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise BoundCodecChildDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (
        kwargs.get("text") is True
        or kwargs.get("universal_newlines") is True
        or kwargs.get("encoding")
    ):
        raise BoundCodecChildDenied("TEXT_MODE_REQUIRED")
    return argv, kwargs, key, profile


def _timeout(kwargs: Mapping[str, Any], maximum: int = 90) -> float:
    raw = kwargs.get("timeout", 60)
    if raw is None:
        raw = 60
    try:
        value = float(raw)
    except Exception as exc:
        raise BoundCodecChildDenied("TIMEOUT_INVALID") from exc
    if not (0 < value <= maximum):
        raise BoundCodecChildDenied("TIMEOUT_OUT_OF_RANGE")
    return value


_WRAPPER = r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
for _k,_v in (spec.get("env") or {}).items():
    os.environ[_k]=_v
if spec.get("cwd"):
    os.chdir(spec["cwd"])
stdin_handle=None
if spec.get("stdin_file"):
    stdin_handle=open(spec["stdin_file"],"rb")
try:
    p=subprocess.run(
        spec["argv"],
        stdin=stdin_handle,
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
finally:
    if stdin_handle is not None:
        stdin_handle.close()
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""


# Same membrane as zero_ambient_namespace_launcher_v1 plus one extra
# read-only bind for /usr/local, because the bound node executable under CI
# is installed at /usr/local/bin and the probe profile stages only scripts.
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


def _resolve_executable(raw: Any, expected: set[str]) -> str:
    token = str(raw)
    base = pathlib.Path(token).name
    if base not in expected:
        raise BoundCodecChildDenied("EXECUTABLE_NOT_ALLOWED:" + base)
    resolved = token if os.path.isabs(token) else shutil.which(token)
    if not resolved:
        raise BoundCodecChildDenied("EXECUTABLE_UNAVAILABLE:" + base)
    p = pathlib.Path(resolved).resolve()
    parent_prefixes = ("/usr/", "/bin/", "/usr/local/")
    if not any(str(p).startswith(prefix) for prefix in parent_prefixes):
        raise BoundCodecChildDenied("EXECUTABLE_PATH_NOT_SYSTEM:" + str(p))
    return str(p)


def _stage_probe_dir(setup: Mapping[str, Any]) -> pathlib.Path:
    """Materialize the single read-only staged input for the probe."""
    stage = pathlib.Path(tempfile.mkdtemp(prefix="brain-codec-probe-input-"))
    for rel, src_cb in setup["files"].items():
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_cb(dst)
    return stage


def _copy_tree(src: pathlib.Path, dst: pathlib.Path) -> None:
    shutil.copytree(src, dst, symlinks=False)


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    argv, kwargs, key, profile = _validate_common(context)
    cwd_raw = kwargs.get("cwd")
    cwd = _path(cwd_raw) if cwd_raw is not None else None

    # Defaults: production codec-run profiles may set a writable stage subdir
    # and a post-run output handoff.
    writable_subdir: "pathlib.Path | None" = None
    output_recover: "tuple[pathlib.Path, pathlib.Path | None] | None" = None
    env_spec: dict[str, str] = {}
    if profile == "ASTRA_VERIFICATION_MISSION_CHILD":
        if len(argv) != 3:
            raise BoundCodecChildDenied("ASTRA_VERIFY_SHAPE_INVALID")
        exe = shutil.which(str(argv[0])) or str(argv[0])
        exe = _path(exe) if os.path.isabs(str(exe)) else None
        if exe is None:
            raise BoundCodecChildDenied("ASTRA_VERIFY_EXECUTABLE_UNAVAILABLE:" + str(argv[0]))
        launcher_path = _path(argv[1])
        if launcher_path != (ROOT / LAUNCHER_REL).resolve() or not launcher_path.is_file():
            raise BoundCodecChildDenied("ASTRA_VERIFY_LAUNCHER_INVALID")
        mission_rel = argv[2]
        mission_path = (ROOT / mission_rel).resolve()
        missions_dir = (ROOT / ASTRA_DIR_REL / "missions").resolve()
        if mission_path.parent != missions_dir or not mission_path.is_file():
            raise BoundCodecChildDenied("ASTRA_VERIFY_MISSION_INVALID")
        if not (exe.name == "python3" or (exe.name.startswith("python3.") and exe.name[8:].isdigit())):
            raise BoundCodecChildDenied("ASTRA_VERIFY_EXECUTABLE_INVALID:" + exe.name)
        exe_token = exe.name
        # The verification child needs the whole repository visible read-only
        # and the canonical/astra_runtime subtree writable for receipts; both
        # binds are materialized in _SETUP_v2 via the dedicated second input.
        input_dir = ROOT
        writable_subdir = (ROOT / ASTRA_DIR_REL).resolve()
        env_spec = {
            "PYTHONPATH": "/input",
            "HOME": "/tmp",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
        }
        inner = [
            exe.name,
            "/input/" + LAUNCHER_REL,
            mission_rel.replace(os.sep, "/"),
        ]
        spec = {
            "argv": inner,
            "cwd": "/input",
            "timeout": _timeout(kwargs, maximum=700),
            "stdin_file": None,
            "env": env_spec,
        }
        staged = None
    elif profile == "NPM_CODEC_CONTRACT_PROBE":
        if len(argv) != 2:
            raise BoundCodecChildDenied("NPM_PROBE_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"node"})
        runner = _path(argv[1])
        runner_expect = (ROOT / NODE_RUNNER_REL).resolve()
        if runner != runner_expect or not runner.is_file():
            raise BoundCodecChildDenied("NPM_PROBE_RUNNER_INVALID")
        raw_input = kwargs.get("input")
        if not isinstance(raw_input, str) or not raw_input:
            raise BoundCodecChildDenied("NPM_PROBE_STDIN_JSON_REQUIRED")
        if len(raw_input.encode("utf-8")) > MAX_INPUT_BYTES:
            raise BoundCodecChildDenied("NPM_PROBE_STDIN_TOO_LARGE")
        try:
            cfg = json.loads(raw_input)
        except Exception as exc:
            raise BoundCodecChildDenied("NPM_PROBE_STDIN_NOT_JSON") from exc
        if not isinstance(cfg, dict) or cfg.get("mode") != "probe":
            raise BoundCodecChildDenied("NPM_PROBE_MODE_INVALID")
        package_root = _path(cfg.get("package_root") or "")
        json_path = _path(cfg.get("json_path") or "")
        if not package_root.is_dir() or not (package_root / "package.json").is_file():
            raise BoundCodecChildDenied("NPM_PROBE_PACKAGE_ROOT_INVALID")
        if not json_path.is_file():
            raise BoundCodecChildDenied("NPM_PROBE_FIXTURE_INVALID")
        if json_path.stat().st_size > 16 * 1024 * 1024:
            raise BoundCodecChildDenied("NPM_PROBE_FIXTURE_TOO_LARGE")
        files = {
            "node_codec_runner.js": (
                lambda dst: dst.write_bytes(runner.read_bytes())
            ),
            "probe_input.json": (lambda dst: dst.write_bytes(raw_input.encode("utf-8"))),
            "fixture.json": (lambda dst: dst.write_bytes(json_path.read_bytes())),
        }
        stage = _stage_probe_dir({"files": files})
        _copy_tree(package_root, stage / "package")
        inner_cfg = dict(cfg)
        inner_cfg["package_root"] = "/input/package"
        inner_cfg["json_path"] = "/input/fixture.json"
        (stage / "probe_input.json").write_text(
            json.dumps(inner_cfg, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        inner = [exe, "/input/node_codec_runner.js"]
        spec = {
            "argv": inner,
            "cwd": "/input",
            "timeout": _timeout(kwargs),
            "stdin_file": "/input/probe_input.json",
        }
        staged = stage
        input_dir = stage
    elif profile == "PY_SOURCE_CODEC_CONTRACT_PROBE":
        if len(argv) != 4:
            raise BoundCodecChildDenied("PY_PROBE_SHAPE_INVALID")
        exe = _path(argv[0])
        probe_helper = _path(argv[1])
        site = _path(argv[2])
        manifest = argv[3]
        if not probe_helper.is_file() or probe_helper.suffix != ".py":
            raise BoundCodecChildDenied("PY_PROBE_HELPER_INVALID")
        if not site.is_dir():
            raise BoundCodecChildDenied("PY_PROBE_SITE_INVALID")
        if not isinstance(manifest, str) or len(manifest) > MAX_INPUT_BYTES:
            raise BoundCodecChildDenied("PY_PROBE_MANIFEST_INVALID")
        try:
            parsed = json.loads(manifest)
        except Exception as exc:
            raise BoundCodecChildDenied("PY_PROBE_MANIFEST_NOT_JSON") from exc
        if not isinstance(parsed, list):
            raise BoundCodecChildDenied("PY_PROBE_MANIFEST_SHAPE_INVALID")
        files = {
            "probe_helper.py": (lambda dst: dst.write_bytes(probe_helper.read_bytes())),
            "probe_manifest.json": (lambda dst: dst.write_bytes(manifest.encode("utf-8"))),
        }
        stage = _stage_probe_dir({"files": files})
        _copy_tree(site, stage / "site")
        inner = [
            str(exe),
            "-I",
            "/input/probe_helper.py",
            "/input/site",
            json.dumps(parsed, sort_keys=True, separators=(",", ":")),
        ]
        spec = {
            "argv": inner,
            "cwd": "/input",
            "timeout": _timeout(kwargs),
            "stdin_file": None,
        }
        staged = stage
        input_dir = stage
    elif profile == "NODE_LIBRARY_CODEC_RUN":
        # Production node codec invocation (bound, verified registry entries):
        # node node_codec_runner.js with a JSON cfg on stdin covering modes
        # encode/decode/decode_verify from verified package+fixture paths.
        if len(argv) != 2:
            raise BoundCodecChildDenied("NODE_RUN_SHAPE_INVALID")
        exe = _resolve_executable(argv[0], {"node"})
        runner = _path(argv[1])
        runner_expect = (ROOT / NODE_RUNNER_REL).resolve()
        if runner != runner_expect or not runner.is_file():
            raise BoundCodecChildDenied("NODE_RUN_RUNNER_INVALID")
        raw_input = kwargs.get("input")
        if not isinstance(raw_input, str) or not raw_input:
            raise BoundCodecChildDenied("NODE_RUN_STDIN_JSON_REQUIRED")
        if len(raw_input.encode("utf-8")) > MAX_INPUT_BYTES:
            raise BoundCodecChildDenied("NODE_RUN_STDIN_TOO_LARGE")
        try:
            cfg = json.loads(raw_input)
        except Exception as exc:
            raise BoundCodecChildDenied("NODE_RUN_STDIN_NOT_JSON") from exc
        mode = cfg.get("mode")
        if not isinstance(cfg, dict) or mode not in {"encode", "decode", "decode_verify"}:
            raise BoundCodecChildDenied("NODE_RUN_MODE_INVALID")
        package_root = _path(cfg.get("package_root") or "")
        if not package_root.is_dir() or not (package_root / "package.json").is_file():
            raise BoundCodecChildDenied("NODE_RUN_PACKAGE_ROOT_INVALID")
        files = {
            "node_codec_runner.js": (lambda dst: dst.write_bytes(runner.read_bytes())),
            "run_input.json": None,
        }
        stage = _stage_probe_dir({"files": {"node_codec_runner.js": files["node_codec_runner.js"]}})
        _copy_tree(package_root, stage / "package")
        inner_cfg = dict(cfg)
        inner_cfg["package_root"] = "/input/package"
        if cfg.get("json_path"):
            json_path = _path(cfg["json_path"])
            if not json_path.is_file():
                raise BoundCodecChildDenied("NODE_RUN_FIXTURE_INVALID")
            (stage / "fixture.json").write_bytes(json_path.read_bytes())
            inner_cfg["json_path"] = "/input/fixture.json"
        if cfg.get("binary_path"):
            binary_path = _path(cfg["binary_path"])
            if not binary_path.is_file():
                raise BoundCodecChildDenied("NODE_RUN_BINARY_INVALID")
            (stage / "binary.bin").write_bytes(binary_path.read_bytes())
            inner_cfg["binary_path"] = "/input/binary.bin"
        writable = stage / "writable"
        writable.mkdir()
        host_output = None
        if mode == "encode" and cfg.get("output_path"):
            host_output = _path(cfg["output_path"])
            try:
                host_output.relative_to(ROOT)
            except ValueError:
                raise BoundCodecChildDenied("NODE_RUN_OUTPUT_PATH_INVALID")
            inner_cfg["output_path"] = "/input/writable/output.bin"
        (stage / "run_input.json").write_text(
            json.dumps(inner_cfg, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        inner = [exe, "/input/node_codec_runner.js"]
        spec = {
            "argv": inner,
            "cwd": "/input",
            "timeout": _timeout(kwargs),
            "stdin_file": "/input/run_input.json",
        }
        staged = stage
        input_dir = stage
        writable_subdir = writable
        output_recover = (stage, host_output)
    elif profile == "PY_SOURCE_TREE_CODEC_RUN":
        if len(argv) != 2:
            raise BoundCodecChildDenied("SRC_TREE_RUN_SHAPE_INVALID")
        exe = _path(argv[0])
        runner = _path(argv[1])
        runner_expect = (ROOT / "canonical" / "runtime" / "github_source_codec_runner.py").resolve()
        if runner != runner_expect or not runner.is_file():
            raise BoundCodecChildDenied("SRC_TREE_RUN_RUNNER_INVALID")
        raw_input = kwargs.get("input")
        if not isinstance(raw_input, str) or not raw_input:
            raise BoundCodecChildDenied("SRC_TREE_RUN_STDIN_JSON_REQUIRED")
        if len(raw_input.encode("utf-8")) > MAX_INPUT_BYTES:
            raise BoundCodecChildDenied("SRC_TREE_RUN_STDIN_TOO_LARGE")
        try:
            cfg = json.loads(raw_input)
        except Exception as exc:
            raise BoundCodecChildDenied("SRC_TREE_RUN_STDIN_NOT_JSON") from exc
        mode = cfg.get("mode")
        if not isinstance(cfg, dict) or mode not in {"encode", "decode", "decode_verify"}:
            raise BoundCodecChildDenied("SRC_TREE_RUN_MODE_INVALID")
        site = _path(cfg.get("_source_root") or "")
        if not site.is_dir():
            raise BoundCodecChildDenied("SRC_TREE_RUN_SITE_INVALID")
        stage = _stage_probe_dir({
            "files": {
                "runner.py": (lambda dst: dst.write_bytes(runner.read_bytes())),
            }
        })
        _copy_tree(site, stage / "site")
        inner_cfg = dict(cfg)
        inner_cfg["_source_root"] = "/input/site"
        if cfg.get("json_path"):
            json_path = _path(cfg["json_path"])
            if not json_path.is_file():
                raise BoundCodecChildDenied("SRC_TREE_RUN_FIXTURE_INVALID")
            (stage / "fixture.json").write_bytes(json_path.read_bytes())
            inner_cfg["json_path"] = "/input/fixture.json"
        if cfg.get("binary_path"):
            binary_path = _path(cfg["binary_path"])
            if not binary_path.is_file():
                raise BoundCodecChildDenied("SRC_TREE_RUN_BINARY_INVALID")
            (stage / "binary.bin").write_bytes(binary_path.read_bytes())
            inner_cfg["binary_path"] = "/input/binary.bin"
        writable = stage / "writable"
        writable.mkdir()
        host_output = None
        if mode == "encode" and cfg.get("output_path"):
            host_output = _path(cfg["output_path"])
            try:
                host_output.relative_to(ROOT)
            except ValueError:
                raise BoundCodecChildDenied("SRC_TREE_RUN_OUTPUT_PATH_INVALID")
            inner_cfg["output_path"] = "/input/writable/output.bin"
        (stage / "run_input.json").write_text(
            json.dumps(inner_cfg, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        inner = [str(exe), "-I", "/input/runner.py"]
        spec = {
            "argv": inner,
            "cwd": "/input",
            "timeout": _timeout(kwargs, maximum=120),
            "stdin_file": "/input/run_input.json",
        }
        staged = stage
        input_dir = stage
        writable_subdir = writable
        output_recover = (stage, host_output)
    else:
        raise BoundCodecChildDenied("PROFILE_UNREACHABLE")

    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    timeout_value = spec["timeout"]
    policy = {
        "argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
        "input_dir": str(input_dir),
        **({"writable_dir": str(writable_subdir)} if writable_subdir is not None else {}),
        "limits": {
            "pids": 128,
            "memory_mb": 1536,
            "cpu_seconds": max(1, min(int(math.ceil(timeout_value)), 300)),
            "wallclock_s": max(1, min(int(math.ceil(timeout_value + 5)), 600)),
            "scratch_mb": 256,
            "max_file_mb": 32,
            "nofile": 128,
            "broker_max_bytes": 8_000_000,
        },
    }
    return {
        "profile": profile,
        "callsite_key": key,
        "original_argv": argv,
        "kwargs": kwargs,
        "policy": policy,
        "timeout": timeout_value,
        "staged_input": staged,
        "output_recover": output_recover,
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
            raise BoundCodecChildDenied(
                "WRITABLE_DIR_NOT_INSIDE_INPUT_BIND"
            ) from exc
        if not writable_rel or writable_rel == ".":
            raise BoundCodecChildDenied("WRITABLE_DIR_MUST_BE_INPUT_SUBPATH")
        if not wp.is_dir():
            raise BoundCodecChildDenied("WRITABLE_DIR_MISSING")
    required_names = ["unshare", "mount", "chroot", "setpriv", "ip", "bash", "env"]
    resolved = {name: ns.resolve_system_binary(name) for name in required_names}
    missing = [name for name, path in resolved.items() if not path]
    if missing:
        raise BoundCodecChildDenied("HOST_PRIMITIVE_MISSING:" + ",".join(missing))
    root = tempfile.mkdtemp(prefix="brain-codec-child-")
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
        str(lim["pids"]),
        str(lim["scratch_mb"]), resolved["setpriv"], "--no-new-privs",
        "--bounding-set=-all",
        "--inh-caps=-all", "--ambient-caps=-all", resolved["env"], "-i",
        "PATH=/usr/local/bin:/usr/bin:/bin",
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
        try:
            _mapped = int(pathlib.Path("/proc/self/uid_map").read_text().split()[1]) != 0
        except Exception:
            _mapped = False
        if not _mapped:
            popen_kw.update(
                user=p["host_uid"], group=p["host_gid"], extra_groups=[]
            )
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
        raise BoundCodecChildDenied("CONFINEMENT_WALLCLOCK_LIMIT_EXCEEDED:" + err_ctx[:400])
    if overflow[0]:
        raise BoundCodecChildDenied("CONFINEMENT_BROKER_OUTPUT_LIMIT_EXCEEDED")
    if rc != 0 and not raw.strip():
        raise BoundCodecChildDenied("CONFINEMENT_WRAPPER_FAILED:" + str(rc) + ": " + err_ctx[:600])
    try:
        result = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BoundCodecChildDenied(
            "CONFINEMENT_BROKER_PAYLOAD_INVALID:raw_len="
            + str(len(raw))
            + ";raw_head="
            + raw[:160].decode("utf-8", "replace")
            + ";err_ctx="
            + err_ctx[:600]
        ) from exc
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
        try:
            result = _run_confined_with_popen(prepared["policy"], popen_impl)
            # Production codec encoders stage their artifact inside the
            # confined writable subdir; hand the bytes back to the declared
            # host output path only on a clean runner completion.
            recover = prepared.get("output_recover")
            if recover is not None and result.get("returncode") == 0:
                stage_dir, host_output = recover
                if host_output is not None:
                    src = stage_dir / "writable" / "output.bin"
                    if src.is_file() and src.stat().st_size > 0:
                        host_output.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, host_output)
        finally:
            shutil.rmtree(prepared["staged_input"], ignore_errors=True)
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
