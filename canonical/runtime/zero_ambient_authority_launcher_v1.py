#!/usr/bin/env python3
"""Fail-closed Docker launch-plan compiler for zero-ambient-authority workers.

This module does not claim that Docker or a particular carrier is independently
verified. It makes the confinement contract mechanical and rejects policies that
would grant undeclared host authority. A separate escape-test receipt is required
before terminal use.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_ZERO_AMBIENT_AUTHORITY_LAUNCHER_V1"
_DIGEST_IMAGE = re.compile(r"^[A-Za-z0-9._/:+-]+@sha256:[0-9a-f]{64}$")
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_ALLOWED_ENV = {"LANG", "LC_ALL", "TZ", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE"}
_FORBIDDEN_ENV_FRAGMENTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL", "COOKIE", "AUTH")
_EFFECT_SENTINEL = "PROJECT_BRAIN_EFFECT_REQUEST_V1:"


class ConfinementError(ValueError):
    pass


def canonical_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise ConfinementError("POLICY_NOT_OBJECT")
    image = str(policy.get("image") or "").strip()
    if not _DIGEST_IMAGE.fullmatch(image):
        raise ConfinementError("IMAGE_MUST_BE_CONTENT_ADDRESSED_SHA256")

    argv_raw = policy.get("argv")
    if not isinstance(argv_raw, Sequence) or isinstance(argv_raw, (str, bytes)) or not argv_raw:
        raise ConfinementError("ARGV_REQUIRED")
    argv = [str(x) for x in argv_raw]
    if any(not x or "\x00" in x for x in argv):
        raise ConfinementError("ARGV_INVALID")

    input_dir = pathlib.Path(str(policy.get("input_dir") or "")).expanduser().resolve()
    if not input_dir.is_dir():
        raise ConfinementError("INPUT_DIR_REQUIRED")

    env_raw = policy.get("env") or {}
    if not isinstance(env_raw, Mapping):
        raise ConfinementError("ENV_NOT_OBJECT")
    env: dict[str, str] = {}
    for raw_k, raw_v in env_raw.items():
        k = str(raw_k)
        v = str(raw_v)
        if not _ENV_NAME.fullmatch(k) or k not in _ALLOWED_ENV:
            raise ConfinementError("ENV_NAME_NOT_ALLOWLISTED:" + k)
        if any(fragment in k for fragment in _FORBIDDEN_ENV_FRAGMENTS):
            raise ConfinementError("ENV_SECRET_LIKE_NAME:" + k)
        if "\x00" in v or len(v) > 512:
            raise ConfinementError("ENV_VALUE_INVALID:" + k)
        env[k] = v

    limits_raw = policy.get("limits") or {}
    if not isinstance(limits_raw, Mapping):
        raise ConfinementError("LIMITS_NOT_OBJECT")
    pids = int(limits_raw.get("pids", 64))
    memory_mb = int(limits_raw.get("memory_mb", 1024))
    cpus = float(limits_raw.get("cpus", 1.0))
    wallclock_s = int(limits_raw.get("wallclock_s", 120))
    scratch_mb = int(limits_raw.get("scratch_mb", 256))
    if not (1 <= pids <= 256):
        raise ConfinementError("PIDS_LIMIT_INVALID")
    if not (64 <= memory_mb <= 16384):
        raise ConfinementError("MEMORY_LIMIT_INVALID")
    if not (0.1 <= cpus <= 8.0):
        raise ConfinementError("CPU_LIMIT_INVALID")
    if not (1 <= wallclock_s <= 3600):
        raise ConfinementError("WALLCLOCK_LIMIT_INVALID")
    if not (16 <= scratch_mb <= 4096):
        raise ConfinementError("SCRATCH_LIMIT_INVALID")

    return {
        "schema": SCHEMA,
        "image": image,
        "argv": argv,
        "input_dir": str(input_dir),
        "env": dict(sorted(env.items())),
        "limits": {
            "pids": pids,
            "memory_mb": memory_mb,
            "cpus": cpus,
            "wallclock_s": wallclock_s,
            "scratch_mb": scratch_mb,
        },
        "authority": {
            "network": "NONE",
            "host_filesystem": "READ_ONLY_SINGLE_INPUT_BIND_ONLY",
            "linux_capabilities": "NONE",
            "privilege_escalation": "DENY_NO_NEW_PRIVILEGES",
            "host_pid_namespace": "DENY",
            "host_ipc_namespace": "DENY",
            "host_credentials": "NONE_BY_ENV_ALLOWLIST",
            "host_devices": "NO_EXPLICIT_DEVICE_GRANTS",
            "mutable_storage": "PRIVATE_TMPFS_ONLY",
            "material_effect_channel": "STDOUT_TYPED_REQUEST_TO_PARENT_ONLY",
        },
    }


def policy_sha256(policy: Mapping[str, Any]) -> str:
    normalized = canonical_policy(policy)
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def docker_argv(policy: Mapping[str, Any]) -> list[str]:
    p = canonical_policy(policy)
    limits = p["limits"]
    args = [
        "docker", "run", "--rm",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=" + str(limits["pids"]),
        "--memory=" + str(limits["memory_mb"]) + "m",
        "--cpus=" + str(limits["cpus"]),
        "--user=65534:65534",
        "--ipc=private",
        "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m",
        "--tmpfs=/work:rw,nosuid,nodev,size=" + str(limits["scratch_mb"]) + "m",
        "--mount=type=bind,src=" + p["input_dir"] + ",dst=/input,readonly",
        "--workdir=/work",
        "--env=HOME=/tmp",
    ]
    for k, v in p["env"].items():
        args.append("--env=" + k + "=" + v)
    args.append(p["image"])
    args.extend(p["argv"])
    return args


def parse_effect_requests(stdout: str) -> list[dict[str, Any]]:
    """Extract typed requests only; ordinary stdout receives no effect authority."""
    out: list[dict[str, Any]] = []
    for line in str(stdout).splitlines():
        if not line.startswith(_EFFECT_SENTINEL):
            continue
        raw = line[len(_EFFECT_SENTINEL):]
        try:
            obj = json.loads(raw)
        except Exception as exc:
            raise ConfinementError("EFFECT_REQUEST_JSON_INVALID") from exc
        if not isinstance(obj, dict):
            raise ConfinementError("EFFECT_REQUEST_NOT_OBJECT")
        typ = str(obj.get("type") or "").strip()
        request_id = str(obj.get("request_id") or "").strip()
        if not typ or not request_id:
            raise ConfinementError("EFFECT_REQUEST_ID_OR_TYPE_MISSING")
        out.append(obj)
    return out


def run_confined(policy: Mapping[str, Any]) -> dict[str, Any]:
    p = canonical_policy(policy)
    argv = docker_argv(p)
    timeout = int(p["limits"]["wallclock_s"])
    proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, env={"PATH": os.environ.get("PATH", "")})
    requests = parse_effect_requests(proc.stdout)
    return {
        "schema": SCHEMA,
        "status": "CHILD_EXITED",
        "policy_sha256": policy_sha256(p),
        "image": p["image"],
        "returncode": proc.returncode,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
        "effect_requests": requests,
        "effect_request_count": len(requests),
        "material_effects_committed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
