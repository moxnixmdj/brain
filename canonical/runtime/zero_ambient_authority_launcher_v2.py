#!/usr/bin/env python3
"""Dedicated broker-channel launcher for Root3 zero-ambient-authority workers.

V2 truth-repairs V1's stdout sentinel. stdout, stderr, exit status, timing, and
resource signals are non-authoritative diagnostics only. The sole positive
child-to-parent authority channel is a framed AF_UNIX socket explicitly mounted
into the confined container.

V2 intentionally commits zero material effects. It validates broker requests
through root3_proof_carrying_effect_v1 and always returns a no-commit response.
That lets transport separation, bounded diagnostics, timeout cleanup, and
auxiliary noninterference be falsified before any real commit broker is enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
from collections.abc import Mapping
from typing import Any, BinaryIO

from canonical.runtime import root3_proof_carrying_effect_v1 as effect_contract
from canonical.runtime import zero_ambient_authority_launcher_v1 as base

SCHEMA = "PROJECT_BRAIN_ZERO_AMBIENT_AUTHORITY_LAUNCHER_V2"
BROKER_SCHEMA = "PROJECT_BRAIN_DEDICATED_EFFECT_BROKER_V1"
BROKER_SOCKET = "/broker/effect.sock"
MAX_FRAME_BYTES = 1_048_576
MAX_BROKER_REQUESTS = 128
MAX_STDOUT_BYTES = 1_048_576
MAX_STDERR_BYTES = 1_048_576


class BrokerError(ValueError):
    pass


def _mount_source(path: pathlib.Path, label: str) -> str:
    value = str(path.resolve())
    if not value or any(ch in value for ch in (",", "\n", "\r", "\x00")):
        raise BrokerError(label + "_UNSAFE_FOR_DOCKER_MOUNT_SYNTAX")
    return value


def carrier_preflight() -> dict[str, Any]:
    """Reject carrier modes whose requested resource controls are not trusted here.

    Rootless Docker is intentionally rejected in V2. Docker documents that rootless
    cgroup flags can be ignored unless cgroup v2 + systemd and controller delegation
    are correctly configured. Rather than infer delegation from weak metadata, this
    cut keeps the trusted carrier surface smaller and requires a rootful Linux daemon.
    """
    if shutil.which("docker") is None:
        raise BrokerError("DOCKER_CLI_MISSING")
    proc = subprocess.run(
        ["docker", "info", "--format", "{{json .}}"],
        text=True,
        capture_output=True,
        timeout=10,
        env={"PATH": os.environ.get("PATH", "")},
        check=False,
    )
    if proc.returncode != 0:
        raise BrokerError("DOCKER_INFO_FAILED")
    try:
        info = json.loads(proc.stdout)
    except Exception as exc:
        raise BrokerError("DOCKER_INFO_JSON_INVALID") from exc
    if not isinstance(info, dict) or str(info.get("OSType") or "").lower() != "linux":
        raise BrokerError("LINUX_DOCKER_REQUIRED")
    security = [str(x).lower() for x in (info.get("SecurityOptions") or [])]
    if any("rootless" in item for item in security):
        raise BrokerError("ROOTLESS_DOCKER_NOT_ADMITTED_V2")
    return {
        "status": "PASS",
        "os_type": "linux",
        "rootless": False,
        "cgroup_driver": str(info.get("CgroupDriver") or ""),
        "cgroup_version": str(info.get("CgroupVersion") or ""),
        "security_options": security,
        "server_version": str(info.get("ServerVersion") or ""),
    }


def docker_argv(
    policy: Mapping[str, Any],
    broker_host_dir: pathlib.Path | str,
    *,
    cidfile: pathlib.Path | str | None = None,
) -> list[str]:
    """Compile the exact Docker authority surface.

    Exactly two host bind mounts are admitted: the declared read-only input and an
    ephemeral read-only directory exposing only the dedicated broker socket.
    """
    p = base.canonical_policy(policy)
    limits = p["limits"]
    input_dir = _mount_source(pathlib.Path(p["input_dir"]), "INPUT_DIR")
    broker_dir = pathlib.Path(broker_host_dir).resolve()
    if not broker_dir.is_dir():
        raise BrokerError("BROKER_HOST_DIR_REQUIRED")
    broker_dir_s = _mount_source(broker_dir, "BROKER_HOST_DIR")

    memory = str(limits["memory_mb"]) + "m"
    args = [
        "docker", "run", "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--security-opt=seccomp=builtin",
        "--cgroupns=private",
        "--pid=private",
        "--ipc=private",
        "--no-healthcheck",
        "--restart=no",
        "--pids-limit=" + str(limits["pids"]),
        "--memory=" + memory,
        "--memory-swap=" + memory,
        "--memory-swappiness=0",
        "--cpus=" + str(limits["cpus"]),
        "--ulimit=nofile=256:256",
        "--ulimit=core=0:0",
        "--shm-size=16m",
        "--user=65534:65534",
        "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m",
        "--tmpfs=/work:rw,nosuid,nodev,size=" + str(limits["scratch_mb"]) + "m",
        "--mount=type=bind,src=" + input_dir + ",dst=/input,readonly",
        "--mount=type=bind,src=" + broker_dir_s + ",dst=/broker,readonly",
        "--workdir=/work",
        "--env=HOME=/tmp",
        "--env=PROJECT_BRAIN_EFFECT_BROKER=" + BROKER_SOCKET,
    ]
    if cidfile is not None:
        cid = pathlib.Path(cidfile).resolve()
        if cid.parent != broker_dir:
            raise BrokerError("CIDFILE_MUST_BE_IN_EPHEMERAL_BROKER_DIR")
        args.append("--cidfile=" + _mount_source(cid, "CIDFILE"))
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
    abort: threading.Event,
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
                    if len(records) >= MAX_BROKER_REQUESTS:
                        abort.set()
                        response = {
                            "schema": BROKER_SCHEMA,
                            "status": "DENIED_NO_COMMIT_V2",
                            "request_id": "",
                            "structural_precommit": {
                                "status": "FAIL_CLOSED",
                                "reason": "BROKER_REQUEST_LIMIT_EXCEEDED",
                            },
                            "material_effect_committed": False,
                            "committed_effect_sha256": None,
                            "auxiliary_observations_used_to_authorize_or_parameterize_effect": False,
                        }
                    else:
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
                        # Missing response can only reduce liveness because V2 has
                        # no commit path and response bytes never authorize effects.
                        pass
    finally:
        ready.set()


def _bounded_reader(
    stream: BinaryIO,
    limit: int,
    sink: bytearray,
    overflow: threading.Event,
) -> None:
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return
        remaining = limit - len(sink)
        if remaining > 0:
            sink.extend(chunk[:remaining])
        if len(chunk) > remaining:
            overflow.set()
            return


def _read_cid(cidfile: pathlib.Path) -> str | None:
    try:
        value = cidfile.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not value or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise BrokerError("CIDFILE_INVALID")
    return value


def _force_remove_container(cidfile: pathlib.Path) -> bool:
    cid = _read_cid(cidfile)
    if cid is None:
        return False
    subprocess.run(
        ["docker", "rm", "-f", cid],
        text=True,
        capture_output=True,
        timeout=10,
        env={"PATH": os.environ.get("PATH", "")},
        check=False,
    )
    return True


def run_confined(
    policy: Mapping[str, Any],
    effect_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Run with one positive authority channel and bounded diagnostics.

    Any timeout, diagnostic overflow, broker-request flood, parse failure, or carrier
    anomaly yields abort/no-commit. A cidfile-backed force-remove path prevents a
    timed-out Docker CLI from leaving an untracked worker container alive.
    """
    carrier = carrier_preflight()
    p = base.canonical_policy(policy)
    timeout = int(p["limits"]["wallclock_s"])
    records: list[dict[str, Any]] = []
    stop = threading.Event()
    ready = threading.Event()
    broker_abort = threading.Event()
    diagnostic_overflow = threading.Event()
    stdout_bytes = bytearray()
    stderr_bytes = bytearray()
    termination_reason = "NORMAL_EXIT"
    cleanup_attempted = False

    with tempfile.TemporaryDirectory(prefix="brain-broker-") as td:
        broker_dir = pathlib.Path(td)
        os.chmod(broker_dir, 0o755)
        socket_path = broker_dir / "effect.sock"
        cidfile = broker_dir / "container.cid"
        thread = threading.Thread(
            target=_serve_broker,
            args=(socket_path, effect_policy, stop, ready, broker_abort, records),
            daemon=True,
        )
        thread.start()
        if not ready.wait(timeout=2.0) or not socket_path.exists():
            stop.set()
            raise BrokerError("BROKER_START_FAILED")

        argv = docker_argv(p, broker_dir, cidfile=cidfile)
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", "")},
        )
        if proc.stdout is None or proc.stderr is None:
            proc.kill()
            raise BrokerError("DOCKER_PIPE_SETUP_FAILED")

        out_thread = threading.Thread(
            target=_bounded_reader,
            args=(proc.stdout, MAX_STDOUT_BYTES, stdout_bytes, diagnostic_overflow),
            daemon=True,
        )
        err_thread = threading.Thread(
            target=_bounded_reader,
            args=(proc.stderr, MAX_STDERR_BYTES, stderr_bytes, diagnostic_overflow),
            daemon=True,
        )
        out_thread.start()
        err_thread.start()

        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if diagnostic_overflow.is_set():
                termination_reason = "DIAGNOSTIC_LIMIT_EXCEEDED"
                break
            if broker_abort.is_set():
                termination_reason = "BROKER_REQUEST_LIMIT_EXCEEDED"
                break
            if time.monotonic() >= deadline:
                termination_reason = "WALLCLOCK_LIMIT_EXCEEDED"
                break
            time.sleep(0.02)

        if proc.poll() is None:
            cleanup_attempted = True
            # First try daemon-side removal using the cidfile. If creation races
            # with this check, kill the client and check the cidfile once more.
            _force_remove_container(cidfile)
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            _force_remove_container(cidfile)

        out_thread.join(timeout=2.0)
        err_thread.join(timeout=2.0)
        stop.set()
        thread.join(timeout=2.0)

        returncode = proc.poll()
        cid_after = _read_cid(cidfile)
        if termination_reason != "NORMAL_EXIT" and cid_after is not None:
            # --rm should remove a terminated container. A surviving inspectable ID
            # is not accepted as proof of cleanup, so attempt removal once more.
            cleanup_attempted = True
            _force_remove_container(cidfile)

    stdout = bytes(stdout_bytes)
    stderr = bytes(stderr_bytes)
    return {
        "schema": SCHEMA,
        "status": "CHILD_EXITED_OR_ABORTED_NO_COMMIT",
        "termination_reason": termination_reason,
        "policy_sha256": base.policy_sha256(p),
        "image": p["image"],
        "returncode": returncode,
        "carrier_preflight": carrier,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_captured_bytes": len(stdout),
        "stderr_captured_bytes": len(stderr),
        "diagnostic_limit_bytes_each": MAX_STDOUT_BYTES,
        "broker_request_count": len(records),
        "broker_request_limit": MAX_BROKER_REQUESTS,
        "broker_records": records,
        "material_effects_committed": 0,
        "positive_authority_channels": ["DEDICATED_AF_UNIX_BROKER_SOCKET"],
        "stdout_effect_authority": False,
        "stderr_effect_authority": False,
        "exit_status_effect_authority": False,
        "timing_effect_authority": False,
        "diagnostic_overflow_effect_authority": False,
        "auxiliary_channels_veto_only": True,
        "timeout_cleanup_attempted": cleanup_attempted,
        "implicit_image_pull_allowed": False,
        "rootless_carrier_admitted": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
