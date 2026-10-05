#!/usr/bin/env python3
"""Dedicated broker-channel launcher for Root3 zero-ambient-authority workers.

V2 truth-repairs V1's stdout sentinel.  stdout/stderr/exit status are diagnostics
only.  The sole positive child-to-parent authority channel is a framed AF_UNIX
socket explicitly mounted into the confined container.

This version intentionally commits zero material effects.  It validates requests
through root3_proof_carrying_effect_v1 and returns a deny/no-commit response while
recording the structural precommit verdict.  That makes transport separation and
auxiliary noninterference testable before any real commit broker is enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import socket
import struct
import subprocess
import tempfile
import threading
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_proof_carrying_effect_v1 as effect_contract
from canonical.runtime import zero_ambient_authority_launcher_v1 as base

SCHEMA = "PROJECT_BRAIN_ZERO_AMBIENT_AUTHORITY_LAUNCHER_V2"
BROKER_SCHEMA = "PROJECT_BRAIN_DEDICATED_EFFECT_BROKER_V1"
BROKER_SOCKET = "/broker/effect.sock"
MAX_FRAME_BYTES = 1_048_576


class BrokerError(ValueError):
    pass


def _mount_source(path: pathlib.Path, label: str) -> str:
    value = str(path.resolve())
    if not value or any(ch in value for ch in (",", "\n", "\r", "\x00")):
        raise BrokerError(label + "_UNSAFE_FOR_DOCKER_MOUNT_SYNTAX")
    return value


def docker_argv(policy: Mapping[str, Any], broker_host_dir: pathlib.Path | str) -> list[str]:
    """Compile the exact Docker authority surface.

    There are exactly two host bind mounts:
      1. the declared input directory, read-only;
      2. an ephemeral directory containing only the dedicated broker socket, read-only.

    No stdout sentinel, host socket, credential directory, Docker socket, or other
    writable host bind is admitted.
    """
    p = base.canonical_policy(policy)
    limits = p["limits"]
    input_dir = _mount_source(pathlib.Path(p["input_dir"]), "INPUT_DIR")
    broker_dir = pathlib.Path(broker_host_dir).resolve()
    if not broker_dir.is_dir():
        raise BrokerError("BROKER_HOST_DIR_REQUIRED")
    broker_dir_s = _mount_source(broker_dir, "BROKER_HOST_DIR")

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
        "--mount=type=bind,src=" + input_dir + ",dst=/input,readonly",
        "--mount=type=bind,src=" + broker_dir_s + ",dst=/broker,readonly",
        "--workdir=/work",
        "--env=HOME=/tmp",
        "--env=PROJECT_BRAIN_EFFECT_BROKER=" + BROKER_SOCKET,
    ]
    for key, value in p["env"].items():
        args.append("--env=" + key + "=" + value)
    args.append(p["image"])
    args.extend(p["argv"])
    return args


def encode_frame(obj: Mapping[str, Any]) -> bytes:
    if not isinstance(obj, Mapping):
        raise BrokerError("FRAME_OBJECT_REQUIRED")
    payload = json.dumps(
        dict(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if not payload or len(payload) > MAX_FRAME_BYTES:
        raise BrokerError("FRAME_SIZE_INVALID")
    return struct.pack(">I", len(payload)) + payload


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        piece = conn.recv(remaining)
        if not piece:
            raise BrokerError("FRAME_TRUNCATED")
        chunks.append(piece)
        remaining -= len(piece)
    return b"".join(chunks)


def recv_frame(conn: socket.socket) -> dict[str, Any]:
    header = _recv_exact(conn, 4)
    (size,) = struct.unpack(">I", header)
    if size < 2 or size > MAX_FRAME_BYTES:
        raise BrokerError("FRAME_SIZE_INVALID")
    raw = _recv_exact(conn, size)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BrokerError("FRAME_JSON_INVALID") from exc
    if not isinstance(obj, dict):
        raise BrokerError("FRAME_OBJECT_REQUIRED")
    return obj


def send_frame(conn: socket.socket, obj: Mapping[str, Any]) -> None:
    conn.sendall(encode_frame(obj))


def evaluate_request_no_commit(
    request: Mapping[str, Any], effect_policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate on the dedicated channel, but never commit in V2."""
    verdict = effect_contract.verify_effect_request(request, effect_policy)
    return {
        "schema": BROKER_SCHEMA,
        "status": "DENIED_NO_COMMIT_V2",
        "request_id": str(request.get("request_id") or ""),
        "structural_precommit": verdict,
        "material_effect_committed": False,
        "committed_effect_sha256": None,
        "auxiliary_observations_used_to_authorize_or_parameterize_effect": False,
    }


def _serve_broker(
    socket_path: pathlib.Path,
    effect_policy: Mapping[str, Any],
    stop: threading.Event,
    ready: threading.Event,
    records: list[dict[str, Any]],
) -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(socket_path))
            os.chmod(socket_path, 0o666)
            server.listen(16)
            server.settimeout(0.1)
            ready.set()
            while not stop.is_set():
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(1.0)
                    try:
                        request = recv_frame(conn)
                        response = evaluate_request_no_commit(request, effect_policy)
                    except Exception as exc:
                        response = {
                            "schema": BROKER_SCHEMA,
                            "status": "DENIED_NO_COMMIT_V2",
                            "request_id": "",
                            "structural_precommit": {
                                "status": "FAIL_CLOSED",
                                "reason": type(exc).__name__ + ":" + str(exc),
                            },
                            "material_effect_committed": False,
                            "committed_effect_sha256": None,
                            "auxiliary_observations_used_to_authorize_or_parameterize_effect": False,
                        }
                    records.append(response)
                    try:
                        send_frame(conn, response)
                    except Exception:
                        # A missing response can only reduce liveness.  It cannot
                        # turn a denied zero-commit V2 request into a host effect.
                        pass
    finally:
        ready.set()


def run_confined(
    policy: Mapping[str, Any],
    effect_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Run a worker with a dedicated broker socket and zero material commits.

    stdout, stderr, return code, timeout and diagnostic variation are observed only
    after/beside broker processing.  None is parsed into a request, effect parameter,
    authority grant, destination, payload, or allow decision.
    """
    p = base.canonical_policy(policy)
    timeout = int(p["limits"]["wallclock_s"])
    records: list[dict[str, Any]] = []
    stop = threading.Event()
    ready = threading.Event()

    with tempfile.TemporaryDirectory(prefix="brain-broker-") as td:
        broker_dir = pathlib.Path(td)
        os.chmod(broker_dir, 0o755)
        socket_path = broker_dir / "effect.sock"
        thread = threading.Thread(
            target=_serve_broker,
            args=(socket_path, effect_policy, stop, ready, records),
            daemon=True,
        )
        thread.start()
        if not ready.wait(timeout=2.0) or not socket_path.exists():
            stop.set()
            raise BrokerError("BROKER_START_FAILED")

        argv = docker_argv(p, broker_dir)
        timed_out = False
        try:
            proc = subprocess.run(
                argv,
                text=True,
                capture_output=True,
                timeout=timeout,
                env={"PATH": os.environ.get("PATH", "")},
            )
            returncode: int | None = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = None
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        finally:
            stop.set()
            thread.join(timeout=2.0)

    return {
        "schema": SCHEMA,
        "status": "CHILD_EXITED_OR_TIMED_OUT",
        "policy_sha256": base.policy_sha256(p),
        "image": p["image"],
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "broker_request_count": len(records),
        "broker_records": records,
        "material_effects_committed": 0,
        "positive_authority_channels": ["DEDICATED_AF_UNIX_BROKER_SOCKET"],
        "stdout_effect_authority": False,
        "stderr_effect_authority": False,
        "exit_status_effect_authority": False,
        "timing_effect_authority": False,
        "auxiliary_channels_veto_only": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
