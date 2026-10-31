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
TOOLCHAIN_DIR = pathlib.Path("/home/user/toolchain_swe/python")
TOOLCHAIN_DIR_S = str(TOOLCHAIN_DIR) if TOOLCHAIN_DIR.is_dir() else None

# The single astra_runtime run_shell subprocess site.
SUPPORTED = {
    ("canonical/runtime/astra_runtime.py", 357, "subprocess.run"): "ASTRA_SHELL_STEP",
    # 2026-10-28 layout: same semantic shell-step launcher rebased.
    ("canonical/runtime/astra_runtime.py", 400, "subprocess.run"): "ASTRA_SHELL_STEP",
}

# 2026-10-28 fleet lighting: verified SWE capabilities run fixed-shape tool
# families (pytest/mypy/coverage/ruff/bandit/unittest/crosshair/git-apply...)
# through the SAME zero-ambient membrane. The repo bind is additionally
# aliased at its absolute host path so module-composed absolute paths resolve
# unchanged inside the chroot.
_BC = "canonical/runtime/bound_capabilities/"
SWE_TOOL_SITES = {
    (_BC + "python_review_diff_coverage_gate.py", 108, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 112, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 122, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 127, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 143, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 154, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_coverage_gate.py", 164, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_mutation_gate.py", 281, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_mutation_gate.py", 292, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_mutation_gate.py", 297, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_mutation_gate.py", 320, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_mutation_gate.py", 373, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_perf_gate.py", 128, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_perf_gate.py", 174, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_perf_gate.py", 190, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_perf_gate.py", 195, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_security_gate.py", 129, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_security_gate.py", 136, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_type_gate.py", 119, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_type_gate.py", 125, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_static_triage.py", 160, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_review_diff_static_triage.py", 166, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repo_diff_apply_full_testgate.py", 100, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repo_diff_apply_full_testgate.py", 111, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repo_diff_apply_full_testgate.py", 116, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repo_diff_apply_full_testgate.py", 130, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repo_pr_realize.py", 69, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_issue_to_pr_orchestrate.py", 485, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_issue_to_pr_orchestrate.py", 597, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_refactor_extract_function.py", 398, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_refactor_rename_parameter.py", 346, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_refactor_rename_symbol.py", 688, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "git_repository_operate.py", 99, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "git_repository_operate.py", 265, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repair_apply_verified_v1.py", 78, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_test_guided_patch_search_v1.py", 59, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_test_guided_patch_search_v1.py", 66, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_tests_generate_scaffold.py", 321, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_tests_generate_scaffold.py", 326, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_tests_generate_scaffold.py", 347, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_dynamic_fault_localizer_v1.py", 58, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_dynamic_fault_localizer_v1.py", 134, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_source_move_function.py", 83, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_source_move_symbol.py", 94, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_source_add_parameter.py", 92, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_feature_implement_function_spec.py", 481, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "software_repair_crossfile_choreograph_v1.py", 144, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "software_repair_crossfile_choreograph_v1.py", 1221, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "software_repair_crossfile_choreograph_v1.py", 1222, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_interprocedural_value_provenance_v1.py", 94, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "code_tree_sitter_patch_verify_v1.py", 101, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_repository_acceptance_measurement_v1.py", 249, "subprocess.run"): "SWE_TOOL_STEP",
    # pynguin test synthesis family: CLI run + generated-suite validation
    (_BC + "python_tests_synthesize_pynguin_v1.py", 64, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "python_tests_synthesize_pynguin_v1.py", 86, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "brain_module_invoke_v1.py", 145, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "source_candidates_verify_git_index.py", 56, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "source_candidates_verify_git_index.py", 83, "subprocess.run"): "SWE_TOOL_STEP",
    (_BC + "crosshair_contract_oracle.py", 51, "subprocess.run"): "SWE_TOOL_STEP",
}
SUPPORTED.update(SWE_TOOL_SITES)

# Tool-family allowlist for SWE_TOOL_STEP (shared with the attempt authorizer).
SWE_PY_MODULES = frozenset(
    {"pytest", "coverage", "mypy", "ruff", "bandit", "unittest", "crosshair",
     "pynguin"}
)
SWE_GIT_SUBCOMMANDS = frozenset(
    {"--version", "apply", "ls-files", "diff", "log", "status", "rev-parse", "show", "-C",
     # pr_realize contract: branch checkout, pinned commit, remote round-trip
     # (remote add/config is done by the harness pre-mediation; the capability
     # itself only READS remotes and PUSHES a content-pinned branch head, then
     # proves it by ls-remote -- identity-safe operations on the local origin)
     "remote", "checkout", "commit", "ls-remote", "push", "add"}
)
SWE_HASH_TOOLS = frozenset({"sha256sum"})
SWE_MAX_CODE_BYTES = 16384
SWE_MAX_ARGV_BYTES = MAX_COMMAND_BYTES if "MAX_COMMAND_BYTES" in dir() else 262_144


def classify_tool_argv(argv: list[str]) -> str:
    """Classify a SWE_TOOL_STEP argv against the fixed tool families.
    Returns the kind string ("python-m", "python-c", "python-I", "git",
    "hashtool") or raises ConfinedShellDenied. Shared by executor and
    authorizer so both gate on the same allowlist by construction."""
    if not isinstance(argv, list) or len(argv) < 2:
        raise ConfinedShellDenied("SWE_TOOL_ARGV_SHAPE_INVALID")
    if any((not isinstance(a, str)) or "\x00" in a for a in argv):
        raise ConfinedShellDenied("SWE_TOOL_ARGV_ELEMENT_INVALID")
    total = sum(len(a.encode("utf-8")) + 1 for a in argv)
    if total > SWE_MAX_ARGV_BYTES:
        raise ConfinedShellDenied("SWE_TOOL_ARGV_TOO_LARGE")
    exe = argv[0]
    base = os.path.basename(exe)
    if base.startswith("python"):
        if argv[1] == "-m":
            if len(argv) < 3 or argv[2] not in SWE_PY_MODULES:
                raise ConfinedShellDenied("SWE_PY_MODULE_NOT_ALLOWED")
            module = argv[2]
            if module == "unittest" and (len(argv) < 4 or argv[3] != "-v"):
                raise ConfinedShellDenied("SWE_UNITTEST_SHAPE_INVALID")
            if module == "crosshair" and (len(argv) < 4 or argv[3] != "check"):
                raise ConfinedShellDenied("SWE_CROSSHAIR_SHAPE_INVALID")
            return "python-m"
        if argv[1] == "-c":
            if len(argv) < 3 or len(argv[2].encode("utf-8")) > SWE_MAX_CODE_BYTES:
                raise ConfinedShellDenied("SWE_CODE_BYTES_OUT_OF_RANGE")
            return "python-c"
        if argv[1] == "-I":
            if len(argv) != 3:
                raise ConfinedShellDenied("SWE_ISOLATED_SCRIPT_SHAPE_INVALID")
            script = pathlib.Path(argv[2])
            try:
                resolved = script.resolve()
                resolved.relative_to(ROOT)
            except Exception as exc:
                raise ConfinedShellDenied("SWE_ISOLATED_SCRIPT_OUTSIDE_ROOT") from exc
            if script.suffix != ".py":
                raise ConfinedShellDenied("SWE_ISOLATED_SCRIPT_NOT_PYTHON")
            return "python-I"
        raise ConfinedShellDenied("SWE_PY_MODE_INVALID")
    if base == "git":
        if argv[1] not in SWE_GIT_SUBCOMMANDS:
            raise ConfinedShellDenied("SWE_GIT_SUBCOMMAND_NOT_ALLOWED:" + argv[1])
        if argv[1] == "-C":
            if len(argv) < 4 or argv[3] not in (
                SWE_GIT_SUBCOMMANDS - {"-C"}
            ):
                raise ConfinedShellDenied("SWE_GIT_C_SUBCOMMAND_INVALID")
        if argv[1] == "apply" and any(a.startswith("-") and a not in (
            "--check", "-v", "--unidiff-zero", "--directory"
        ) for a in argv[2:]):
            raise ConfinedShellDenied("SWE_GIT_APPLY_FIELD_INVALID")
        return "git"
    if base in SWE_HASH_TOOLS:
        return "hashtool"
    raise ConfinedShellDenied("SWE_TOOL_EXECUTABLE_INVALID:" + base)

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
ROOT="$1"; INPUT="$2"; RWSUB="$3"; BROKER="$4"; MEM_KB="$5"; CPU_S="$6"; FILE_KB="$7"; NOFILE="$8"; PIDS="$9"; SCRATCH_MB="${10}"; ALIAS="${11}"; TOOLCHAIN="${12}"; shift 12
mount --make-rprivate /
mount -t tmpfs -o size=96m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/dev" "$ROOT/proc" "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/input"
if [ "$ALIAS" != "-" ]; then mkdir -p "$ROOT$ALIAS"; fi
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
if [ "$ALIAS" != "-" ]; then
  mount --bind "$INPUT" "$ROOT$ALIAS"
  mount -o remount,bind,ro,nosuid,nodev "$ROOT$ALIAS"
  if [ "$RWSUB" != "-" ]; then
    mkdir -p "$ROOT$ALIAS/$RWSUB"
    mount --bind "$INPUT/$RWSUB" "$ROOT$ALIAS/$RWSUB"
    mount -o remount,bind,nosuid,nodev "$ROOT$ALIAS/$RWSUB"
  fi
fi
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"
if [ "$TOOLCHAIN" != "-" ]; then
  mkdir -p "$ROOT/tmp/.local/lib/python3.11/site-packages"
  mount --bind "$TOOLCHAIN" "$ROOT/tmp/.local/lib/python3.11/site-packages"
  mount -o remount,bind,ro,nosuid,nodev "$ROOT/tmp/.local/lib/python3.11/site-packages"
fi
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
    if profile == "SWE_TOOL_STEP":
        return _validate_tool(context, key, profile)
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


def _validate_tool(
    context: Mapping[str, Any], key: tuple[str, int, str], profile: str
) -> dict[str, Any]:
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise ConfinedShellDenied("SWE_TOOL_POSITIONAL_SHAPE_INVALID")
    argv0 = args[0]
    if not isinstance(argv0, (list, tuple)):
        raise ConfinedShellDenied("SWE_TOOL_ARGV_NOT_LIST")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else x for x in argv0]
    kind = classify_tool_argv(list(argv))
    kwargs = context.get("kwargs")
    if not isinstance(kwargs, Mapping):
        raise ConfinedShellDenied("SWE_TOOL_KWARGS_INVALID")
    if kwargs.get("input") is not None:
        raise ConfinedShellDenied("SWE_TOOL_INPUT_FORBIDDEN")
    if kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise ConfinedShellDenied("SWE_TOOL_STDIN_HANDLE_FORBIDDEN")
    cwd_value = kwargs.get("cwd")
    if cwd_value is not None:
        try:
            cwd_value = str(os.fspath(cwd_value))
        except Exception as exc:
            raise ConfinedShellDenied("SWE_TOOL_CWD_INVALID") from exc
        try:
            pathlib.Path(cwd_value).resolve().relative_to(ROOT)
        except ValueError as exc:
            raise ConfinedShellDenied("SWE_TOOL_CWD_OUTSIDE_REPO") from exc
    timeout = kwargs.get("timeout", 300)
    if timeout is None:
        timeout = 300
    try:
        timeout_value = float(timeout)
    except Exception as exc:
        raise ConfinedShellDenied("TIMEOUT_INVALID") from exc
    if not (0.0 < timeout_value <= 300.0):
        raise ConfinedShellDenied("SWE_TOOL_TIMEOUT_OUT_OF_RANGE")
    env_spec: dict[str, str] = {}
    raw_env = kwargs.get("env")
    if isinstance(raw_env, Mapping):
        for k2, v2 in raw_env.items():
            k2 = str(k2)
            v2 = str(v2)
            if not k2 or "\x00" in v2 or len(v2) > 8192:
                raise ConfinedShellDenied("SWE_TOOL_ENV_VALUE_INVALID")
            env_spec[k2] = v2
    return {
        "argv": [str(a) for a in argv],
        "kind": kind,
        "kwargs": kwargs,
        "timeout": timeout_value,
        "env": env_spec,
        "key": key,
        "profile": profile,
    }


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    v = _validate(context)
    if v["profile"] == "SWE_TOOL_STEP":
        exe = v["argv"][0]
        exe_abs = None
        if os.path.isabs(exe) and os.path.isfile(exe):
            exe_abs = str(pathlib.Path(exe).resolve())
        else:
            exe_abs = shutil.which(exe)
        if not exe_abs:
            raise ConfinedShellDenied("SWE_TOOL_EXECUTABLE_UNAVAILABLE:" + exe)
        inner = [str(exe_abs), *v["argv"][1:]]
        tool_cwd = v["kwargs"].get("cwd") or str(ROOT)
        spec = {
            # The host repo root is bind-mounted at BOTH /input and (via the
            # alias mount) its own absolute host path, so module-composed
            # absolute paths and cwd resolve unchanged inside the chroot.
            "argv": inner,
            "cwd": str(tool_cwd),
            "timeout": v["timeout"],
            "stdin_file": None,
            "env": {
                # Tool caches on the writable private scratch, never the
                # read-only repo bind.
                "MYPY_CACHE_DIR": "/tmp/.mypy_cache",
                "RUFF_CACHE_DIR": "/tmp/.ruff_cache",
                "COVERAGE_FILE": "/tmp/.coverage",
                "PYTHONDONTWRITEBYTECODE": "1",
                **v["env"],
                "PYTHONPATH": "/input:/tmp/.local/lib/python3.11/site-packages",
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
            "alias_dir": str(ROOT),
            "toolchain_dir": TOOLCHAIN_DIR_S,
            "limits": {
                # Caps enforced by zero_ambient_namespace_launcher_v1.canonical_policy.
                "pids": 128,
                "memory_mb": 4096,
                "cpu_seconds": max(60, min(int(math.ceil(v["timeout"])), 300)),
                "wallclock_s": max(120, min(int(math.ceil(v["timeout"] + 10)), 600)),
                "scratch_mb": 768,
                "max_file_mb": 256,
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
        (str(policy.get("alias_dir")) if policy.get("alias_dir") else "-"),
        (str(policy.get("toolchain_dir")) if policy.get("toolchain_dir") else "-"),
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
