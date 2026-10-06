from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_broker_rpc_v1 as rpc
from canonical.runtime import zero_ambient_namespace_launcher_v1 as base

SCHEMA = "PROJECT_BRAIN_ZERO_AMBIENT_NAMESPACE_BROKERED_LAUNCHER_V2"


class BrokeredNamespaceError(RuntimeError):
    pass


def run_confined_brokered(
    policy: Mapping[str, Any],
    handler: Callable[[dict[str, Any]], Any],
    *,
    max_requests: int = 1024,
) -> dict[str, Any]:
    p = base.canonical_policy(policy)
    lim = p["limits"]

    required_names = ["unshare", "mount", "chroot", "setpriv", "ip", "bash", "env"]
    resolved = {name: shutil.which(name) for name in required_names}
    missing = [name for name, path in resolved.items() if not path]
    if missing:
        raise BrokeredNamespaceError(
            "HOST_PRIMITIVE_MISSING:" + ",".join(missing)
        )

    root = tempfile.mkdtemp(prefix="brain-ns-broker-v2-")
    os.chown(root, p["host_uid"], p["host_gid"])
    parent, child = socket.socketpair()
    broker_result: dict[str, Any] = {}
    broker_error: list[str] = []

    def broker_thread() -> None:
        try:
            broker_result.update(
                rpc.serve_loop(
                    parent,
                    handler,
                    max_requests=max_requests,
                    max_frame_bytes=lim["broker_max_bytes"],
                )
            )
        except Exception as exc:
            broker_error.append(type(exc).__name__ + ":" + str(exc))

    th = threading.Thread(target=broker_thread, daemon=True)
    th.start()

    env = {
        "BROKER_FD": str(child.fileno()),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for k, v in p["env"].items():
        env[k] = v

    cmd = [
        resolved["unshare"],
        "--user",
        "--map-root-user",
        "--mount",
        "--net",
        "--pid",
        "--fork",
        "--ipc",
        "--uts",
        resolved["bash"],
        "-c",
        base._SETUP,
        "_",
        root,
        p["input_dir"],
        str(child.fileno()),
        str(lim["memory_mb"] * 1024),
        str(lim["cpu_seconds"]),
        str((lim["max_file_mb"] * 1024 + 1023) // 1024),
        str(lim["nofile"]),
        str(lim["pids"]),
        str(lim["scratch_mb"]),
        resolved["setpriv"],
        "--no-new-privs",
        "--bounding-set=-all",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        resolved["env"],
        "-i",
        "PATH=/usr/bin:/bin",
        "HOME=/tmp",
        "PYTHONDONTWRITEBYTECODE=1",
        "PROJECT_BRAIN_BROKER_FD=" + str(child.fileno()),
    ]
    for k, v in p["env"].items():
        cmd.append(k + "=" + v)
    cmd += p["argv"]

    popen_kw: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "pass_fds": (child.fileno(),),
        "env": env,
        "start_new_session": True,
    }
    if os.geteuid() == 0:
        popen_kw.update(
            user=p["host_uid"],
            group=p["host_gid"],
            extra_groups=[],
        )

    started = time.monotonic()
    timed_out = False
    rc = -1
    try:
        proc = subprocess.Popen(cmd, **popen_kw)
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

    if th.is_alive():
        status = "BROKER_THREAD_DID_NOT_TERMINATE"
    elif broker_error:
        status = "BROKER_PROTOCOL_ERROR"
    elif timed_out:
        status = "WALLCLOCK_LIMIT_EXCEEDED"
    else:
        status = "CHILD_EXITED"

    return {
        "schema": SCHEMA,
        "status": status,
        "base_policy_sha256": base.policy_sha256(p),
        "returncode": rc,
        "wallclock_ms": round((time.monotonic() - started) * 1000, 3),
        "broker_status": broker_result.get("status"),
        "broker_requests_served": broker_result.get("requests_served", 0),
        "broker_error": broker_error[0] if broker_error else None,
        "material_effects_committed_by_launcher": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "terminal_credit_delta": 0,
    }
