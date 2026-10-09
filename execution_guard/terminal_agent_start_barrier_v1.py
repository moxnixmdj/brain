#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

READY_SCHEMA = "PROJECT_BRAIN_AGENT_START_READY_V1"
COMMIT_SCHEMA = "PROJECT_BRAIN_AGENT_START_COMMIT_V1"
DEFAULT_TIMEOUT_S = 600.0
DEFAULT_POLL_S = 0.05


class AgentStartBarrierError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _required_env(name: str, maximum: int = 4096) -> str:
    value = os.environ.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AgentStartBarrierError("ENV_REQUIRED:" + name)
    return value.strip()


def _validate_task_digest(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise AgentStartBarrierError("TASK_DIGEST_INVALID")
    return value


def _safe_barrier_dir(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise AgentStartBarrierError("BARRIER_DIR_INVALID")
    return path


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    raw = _canonical_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    with open(tmp, "wb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AgentStartBarrierError("JSON_READ_FAILED:" + path.name) from exc
    if not isinstance(value, dict):
        raise AgentStartBarrierError("JSON_OBJECT_REQUIRED:" + path.name)
    return value


def barrier_paths() -> tuple[Path, Path]:
    root = _safe_barrier_dir(_required_env("BRAIN_AGENT_START_BARRIER_DIR"))
    return root / "AGENT_READY.json", root / "START_COMMITTED.json"


def build_ready(logical_attempt_id: str) -> dict[str, Any]:
    if not _valid_sha256(logical_attempt_id):
        raise AgentStartBarrierError("LOGICAL_ATTEMPT_ID_INVALID")
    return {
        "schema": READY_SCHEMA,
        "slot_id": _required_env("BRAIN_SLOT_ID"),
        "task_digest": _validate_task_digest(_required_env("BRAIN_TASK_DIGEST")),
        "logical_attempt_id": logical_attempt_id,
        "pid": os.getpid(),
        "task_started": False,
        "benchmark_trials_consumed": 0,
    }


def publish_ready(logical_attempt_id: str) -> tuple[Path, dict[str, Any], str]:
    ready_path, _commit_path = barrier_paths()
    if ready_path.exists():
        existing = _read_json(ready_path)
        candidate = build_ready(logical_attempt_id)
        for key in ("schema", "slot_id", "task_digest", "logical_attempt_id"):
            if existing.get(key) != candidate.get(key):
                raise AgentStartBarrierError("READY_ALREADY_EXISTS_WITH_DIFFERENT_IDENTITY:" + key)
        ready = existing
    else:
        ready = build_ready(logical_attempt_id)
        _atomic_write_json(ready_path, ready)
    return ready_path, ready, _sha256_file(ready_path)


def validate_commit(
    commit: dict[str, Any],
    *,
    logical_attempt_id: str,
    ready_sha256: str,
) -> dict[str, Any]:
    expected = {
        "schema": COMMIT_SCHEMA,
        "slot_id": _required_env("BRAIN_SLOT_ID"),
        "task_digest": _validate_task_digest(_required_env("BRAIN_TASK_DIGEST")),
        "logical_attempt_id": logical_attempt_id,
        "agent_ready_receipt_sha256": ready_sha256,
        "start_cas_acquired": True,
        "task_started": True,
        "benchmark_trials_consumed": 1,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }
    for key, value in expected.items():
        if commit.get(key) != value:
            raise AgentStartBarrierError("START_COMMIT_INVALID:" + key)
    for key in (
        "start_cas_receipt_sha256",
        "durable_start_record_sha256",
        "runtime_identity_sha256",
    ):
        if not _valid_sha256(commit.get(key)):
            raise AgentStartBarrierError("START_COMMIT_INVALID:" + key)
    return commit


async def await_start_commit(
    logical_attempt_id: str,
    *,
    timeout_s: float | None = None,
    poll_s: float = DEFAULT_POLL_S,
) -> dict[str, Any]:
    if not _valid_sha256(logical_attempt_id):
        raise AgentStartBarrierError("LOGICAL_ATTEMPT_ID_INVALID")
    if timeout_s is None:
        raw = os.environ.get("BRAIN_AGENT_START_BARRIER_TIMEOUT_S")
        timeout_s = float(raw) if raw else DEFAULT_TIMEOUT_S
    if timeout_s <= 0 or poll_s <= 0:
        raise AgentStartBarrierError("BARRIER_TIMING_INVALID")

    ready_path, _ready, ready_sha256 = publish_ready(logical_attempt_id)
    _ready_path_check, commit_path = barrier_paths()
    if _ready_path_check != ready_path:
        raise AgentStartBarrierError("BARRIER_PATH_CHANGED_DURING_WAIT")

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        if commit_path.is_file():
            commit = _read_json(commit_path)
            return validate_commit(
                commit,
                logical_attempt_id=logical_attempt_id,
                ready_sha256=ready_sha256,
            )
        if loop.time() >= deadline:
            raise AgentStartBarrierError("START_COMMIT_TIMEOUT__NO_AGENT_ACTION")
        await asyncio.sleep(poll_s)


def build_commit_from_cas(
    *,
    ready_path: Path,
    cas_receipt_path: Path,
) -> dict[str, Any]:
    ready = _read_json(ready_path)
    cas = _read_json(cas_receipt_path)
    ready_sha256 = _sha256_file(ready_path)

    if ready.get("schema") != READY_SCHEMA:
        raise AgentStartBarrierError("READY_SCHEMA_INVALID")
    if cas.get("acquired") is not True or cas.get("task_started") is not True:
        raise AgentStartBarrierError("START_CAS_NOT_ACQUIRED")
    if cas.get("benchmark_trials_consumed") != 1:
        raise AgentStartBarrierError("START_CAS_CONSUMPTION_INVALID")
    for key in ("slot_id", "task_digest", "logical_attempt_id"):
        if cas.get(key) != ready.get(key):
            raise AgentStartBarrierError("START_CAS_READY_IDENTITY_MISMATCH:" + key)
    if cas.get("agent_ready_receipt_sha256") != ready_sha256:
        raise AgentStartBarrierError("START_CAS_READY_SHA_MISMATCH")
    if cas.get("replay_authority") is not False:
        raise AgentStartBarrierError("START_CAS_REPLAY_AUTHORITY_INVALID")
    if cas.get("replacement_carrier_authority") is not False:
        raise AgentStartBarrierError("START_CAS_REPLACEMENT_AUTHORITY_INVALID")

    for key in (
        "durable_record_sha256",
        "runtime_identity_sha256",
    ):
        if not _valid_sha256(cas.get(key)):
            raise AgentStartBarrierError("START_CAS_FIELD_INVALID:" + key)

    return {
        "schema": COMMIT_SCHEMA,
        "slot_id": ready["slot_id"],
        "task_digest": ready["task_digest"],
        "logical_attempt_id": ready["logical_attempt_id"],
        "agent_ready_receipt_sha256": ready_sha256,
        "start_cas_receipt_sha256": _sha256_file(cas_receipt_path),
        "durable_start_record_sha256": cas["durable_record_sha256"],
        "runtime_identity_sha256": cas["runtime_identity_sha256"],
        "start_cas_acquired": True,
        "task_started": True,
        "benchmark_trials_consumed": 1,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }


def release_from_cas(
    *,
    ready_path: Path,
    cas_receipt_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    commit = build_commit_from_cas(
        ready_path=ready_path,
        cas_receipt_path=cas_receipt_path,
    )
    if output_path.exists():
        existing = _read_json(output_path)
        if _canonical_bytes(existing) != _canonical_bytes(commit):
            raise AgentStartBarrierError("START_COMMIT_ALREADY_EXISTS_WITH_DIFFERENT_BYTES")
        return existing
    _atomic_write_json(output_path, commit)
    return commit


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    release = sub.add_parser("release")
    release.add_argument("--ready", required=True)
    release.add_argument("--cas-receipt", required=True)
    release.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.command == "release":
            result = release_from_cas(
                ready_path=Path(args.ready).resolve(),
                cas_receipt_path=Path(args.cas_receipt).resolve(),
                output_path=Path(args.output).resolve(),
            )
        else:
            raise AgentStartBarrierError("UNKNOWN_COMMAND")
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, sort_keys=True))
        return 1
    print(json.dumps({"status": "PASS", "commit": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
