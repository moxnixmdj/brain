#!/usr/bin/env python3
"""Provider-neutral same-identity supervisor for Project Brain.

This module intentionally reuses the already-promoted ASTRA runtime rather
than implementing cognition, planning, or capability acquisition again.

Authority model:
- immutable task manifests live in the canonical repository;
- one durable worker identity claims only causally-ready tasks;
- a task SHA binds dedupe/provenance;
- a durable state file binds lease ownership and continuation;
- the child ASTRA runtime receives the same agent/task identity through env;
- this supervisor never self-promotes or mutates canonical population truth.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable
from canonical.runtime import continuous_obs_runtime

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASK_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1"
STATE_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_STATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_EXECUTION_RECEIPT_V1"
DEFAULT_AGENT_ID = "SUPERWORKER-UNIFIED-1"


class SupervisorError(RuntimeError):
    pass


class NoCausallyReadyTask(SupervisorError):
    pass


class LeaseConflict(SupervisorError):
    pass


class TaskAlreadyTerminal(SupervisorError):
    pass


def _utc_epoch() -> int:
    return int(time.time())


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: pathlib.Path) -> str:
    return _sha_bytes(path.read_bytes())


def _sha_text(text: str) -> str:
    return _sha_bytes(text.encode("utf-8"))


def _canonical_json_sha(value: Any) -> str:
    return _sha_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", text):
        raise SupervisorError(f"{field}_INVALID")
    return text


def _repo_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = root.resolve()
    value = str(raw or "").strip().replace("\\", "/")
    if value.startswith("/"):
        value = value.lstrip("/")
    path = (root / pathlib.PurePosixPath(value)).resolve()
    if path == root or root not in path.parents:
        raise SupervisorError("PATH_OUTSIDE_REPOSITORY")
    return path


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SupervisorError("JSON_OBJECT_REQUIRED")
    return value


def _write_json_atomic(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


@contextlib.contextmanager
def _claim_lock(state_dir: pathlib.Path, stale_after_s: int = 120):
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / ".claim.lock"
    now = _utc_epoch()
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = now - int(lock.stat().st_mtime)
        except FileNotFoundError:
            age = 0
        if age > stale_after_s:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        else:
            raise LeaseConflict("CLAIM_LOCK_HELD")
    try:
        os.write(fd, f"{os.getpid()}:{now}\n".encode())
        os.close(fd)
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def _validate_task(task: dict[str, Any], agent_id: str) -> dict[str, Any]:
    if task.get("schema") != TASK_SCHEMA:
        raise SupervisorError("TASK_SCHEMA_INVALID")
    task_id = _safe_id(task.get("task_id"), "TASK_ID")
    declared_agent = _safe_id(task.get("agent_id"), "AGENT_ID")
    if declared_agent != agent_id:
        raise SupervisorError("WRONG_AGENT")
    if float(task.get("incremental_spend_usd", 0)) != 0.0:
        raise SupervisorError("NONZERO_INCREMENTAL_SPEND")
    mission_path = str(task.get("mission_path") or "").strip()
    mission_sha = str(task.get("mission_sha256") or "").strip().lower()
    if not mission_path or not re.fullmatch(r"[0-9a-f]{64}", mission_sha):
        raise SupervisorError("MISSION_BINDING_INVALID")
    priority = int(task.get("priority", 50))
    if priority < -1000000 or priority > 1000000:
        raise SupervisorError("PRIORITY_OUT_OF_RANGE")
    prerequisites = task.get("prerequisites", [])
    if not isinstance(prerequisites, list):
        raise SupervisorError("PREREQUISITES_INVALID")
    return {
        **task,
        "task_id": task_id,
        "agent_id": declared_agent,
        "mission_path": mission_path,
        "mission_sha256": mission_sha,
        "priority": priority,
        "prerequisites": prerequisites,
    }


def _prerequisites_satisfied(root: pathlib.Path, task: dict[str, Any]) -> bool:
    for raw in task.get("prerequisites", []):
        if isinstance(raw, str):
            path = _repo_path(root, raw)
            expected = None
        elif isinstance(raw, dict):
            path = _repo_path(root, raw.get("path"))
            expected = str(raw.get("sha256") or "").strip().lower() or None
        else:
            raise SupervisorError("PREREQUISITE_INVALID")
        if not path.is_file():
            return False
        if expected is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise SupervisorError("PREREQUISITE_HASH_INVALID")
            if _sha_file(path) != expected:
                return False
    return True


def _state_path(state_dir: pathlib.Path, task_id: str) -> pathlib.Path:
    return state_dir / f"{task_id}.json"


def _load_state(state_dir: pathlib.Path, task_id: str) -> dict[str, Any] | None:
    path = _state_path(state_dir, task_id)
    return _read_json(path) if path.is_file() else None


def _task_sha(task: dict[str, Any]) -> str:
    return _canonical_json_sha(task)


def _new_state(task: dict[str, Any], agent_id: str, lease_seconds: int) -> dict[str, Any]:
    now = _utc_epoch()
    lease_id = uuid.uuid4().hex
    return {
        "schema": STATE_SCHEMA,
        "agent_id": agent_id,
        "task_id": task["task_id"],
        "task_sha256": _task_sha(task),
        "mission_path": task["mission_path"],
        "mission_sha256": task["mission_sha256"],
        "status": "CLAIMED",
        "lease": {
            "owner": agent_id,
            "lease_id": lease_id,
            "acquired_at_epoch": now,
            "expires_at_epoch": now + lease_seconds,
        },
        "claim_count": 1,
        "checkpoint_count": 0,
        "runtime_attempt_count": 0,
        "events": [{
            "seq": 1,
            "type": "TASK_ACQUIRED",
            "epoch": now,
            "owner": agent_id,
            "lease_id_sha256": _sha_text(lease_id),
        }],
        "promotion_claim": False,
        "p_real_claim": 0,
    }


def _append_event(state: dict[str, Any], event_type: str, **payload: Any) -> None:
    events = state.setdefault("events", [])
    events.append({
        "seq": len(events) + 1,
        "type": event_type,
        "epoch": _utc_epoch(),
        **payload,
    })


def _validate_existing_state(
    state: dict[str, Any],
    task: dict[str, Any],
    agent_id: str,
    lease_seconds: int,
) -> dict[str, Any]:
    if state.get("schema") != STATE_SCHEMA:
        raise SupervisorError("STATE_SCHEMA_INVALID")
    if state.get("agent_id") != agent_id:
        raise LeaseConflict("STATE_AGENT_ID_MISMATCH")
    if state.get("task_id") != task["task_id"]:
        raise SupervisorError("STATE_TASK_ID_MISMATCH")
    if state.get("task_sha256") != _task_sha(task):
        raise SupervisorError("TASK_MANIFEST_DRIFT")
    if state.get("mission_sha256") != task["mission_sha256"]:
        raise SupervisorError("STATE_MISSION_SHA_MISMATCH")
    if state.get("status") in {"COMPLETE", "FAILED"}:
        raise TaskAlreadyTerminal(state.get("status"))
    lease = dict(state.get("lease") or {})
    if lease.get("owner") != agent_id:
        raise LeaseConflict("LEASE_OWNER_MISMATCH")
    now = _utc_epoch()
    lease["expires_at_epoch"] = now + lease_seconds
    state["lease"] = lease
    state["claim_count"] = int(state.get("claim_count", 0)) + 1
    _append_event(state, "TASK_RESUMED", owner=agent_id)
    return state


def claim_task(
    root: pathlib.Path,
    task_path: pathlib.Path,
    state_dir: pathlib.Path,
    agent_id: str = DEFAULT_AGENT_ID,
    lease_seconds: int = 900,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    task = _validate_task(_read_json(task_path), agent_id)
    if not _prerequisites_satisfied(root, task):
        raise NoCausallyReadyTask("PREREQUISITES_UNSATISFIED")
    mission = _repo_path(root, task["mission_path"])
    if not mission.is_file():
        raise NoCausallyReadyTask("MISSION_MISSING")
    if _sha_file(mission) != task["mission_sha256"]:
        raise SupervisorError("MISSION_SHA_MISMATCH")
    mission_doc = _read_json(mission)
    obs_verdict = continuous_obs_runtime.validate_context(
        mission_doc.get("continuous_obs"),
        root=root,
    )
    if not obs_verdict.get("pass"):
        raise NoCausallyReadyTask(
            "CONTINUOUS_OBS_NOT_CURRENT:"+"|".join(obs_verdict.get("errors") or ["UNKNOWN"])
        )

    with _claim_lock(state_dir):
        state = _load_state(state_dir, task["task_id"])
        if state is None:
            state = _new_state(task, agent_id, lease_seconds)
        else:
            state = _validate_existing_state(state, task, agent_id, lease_seconds)
        _write_json_atomic(_state_path(state_dir, task["task_id"]), state)
    return task, state


def choose_causally_ready_task(
    root: pathlib.Path,
    tasks_dir: pathlib.Path,
    state_dir: pathlib.Path,
    agent_id: str = DEFAULT_AGENT_ID,
) -> pathlib.Path:
    candidates: list[tuple[int, str, pathlib.Path]] = []
    for path in sorted(tasks_dir.glob("*.json")):
        try:
            task = _validate_task(_read_json(path), agent_id)
        except SupervisorError:
            continue
        state = _load_state(state_dir, task["task_id"])
        if state and state.get("status") in {"COMPLETE", "FAILED"}:
            continue
        if not _prerequisites_satisfied(root, task):
            continue
        mission = _repo_path(root, task["mission_path"])
        if not mission.is_file() or _sha_file(mission) != task["mission_sha256"]:
            continue
        try:
            mission_doc = _read_json(mission)
            obs_verdict = continuous_obs_runtime.validate_context(
                mission_doc.get("continuous_obs"),
                root=root,
            )
        except Exception:
            continue
        if not obs_verdict.get("pass"):
            continue
        candidates.append((-int(task["priority"]), task["task_id"], path))
    if not candidates:
        raise NoCausallyReadyTask("NO_CAUSALLY_READY_TASK")
    candidates.sort()
    return candidates[0][2]


@dataclass
class RuntimeResult:
    returncode: int
    stdout: str
    stderr: str


RuntimeExecutor = Callable[[list[str], pathlib.Path, dict[str, str]], RuntimeResult]


def _default_executor(argv: list[str], cwd: pathlib.Path, env: dict[str, str]) -> RuntimeResult:
    proc = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True)
    return RuntimeResult(proc.returncode, proc.stdout, proc.stderr)


def execute_claimed_task(
    root: pathlib.Path,
    task: dict[str, Any],
    state_dir: pathlib.Path,
    evidence_dir: pathlib.Path,
    agent_id: str = DEFAULT_AGENT_ID,
    executor: RuntimeExecutor = _default_executor,
) -> tuple[int, dict[str, Any]]:
    state_path = _state_path(state_dir, task["task_id"])
    state = _load_state(state_dir, task["task_id"])
    if state is None:
        raise SupervisorError("TASK_NOT_CLAIMED")
    if state.get("agent_id") != agent_id or state.get("task_sha256") != _task_sha(task):
        raise SupervisorError("CLAIM_BINDING_INVALID")

    if bool(task.get("checkpoint_before_runtime_once")) and int(state.get("checkpoint_count", 0)) == 0:
        state["checkpoint_count"] = 1
        state["status"] = "CHECKPOINTED_RELAUNCH_REQUIRED"
        _append_event(state, "CHECKPOINT_CREATED", reason="TASK_REQUESTED_PRE_RUNTIME_RELAUNCH")
        _write_json_atomic(state_path, state)
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "agent_id": agent_id,
            "task_id": task["task_id"],
            "task_sha256": state["task_sha256"],
            "mission_sha256": task["mission_sha256"],
            "status": "CHECKPOINTED_RELAUNCH_REQUIRED",
            "same_identity_bound": True,
            "promotion_claim": False,
            "p_real_claim": 0,
            "incremental_spend_usd": 0,
        }
        evidence_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(evidence_dir / f"{task['task_id']}__CHECKPOINT.json", receipt)
        return 75, receipt

    mission = _repo_path(root, task["mission_path"])
    if _sha_file(mission) != task["mission_sha256"]:
        raise SupervisorError("MISSION_SHA_MISMATCH_BEFORE_EXECUTION")
    mission_doc = _read_json(mission)
    obs_verdict = continuous_obs_runtime.validate_context(
        mission_doc.get("continuous_obs"),
        root=root,
    )
    if not obs_verdict.get("pass"):
        raise SupervisorError(
            "CONTINUOUS_OBS_BLOCKED_BEFORE_EXECUTION:"
            +"|".join(obs_verdict.get("errors") or ["UNKNOWN"])
        )

    state["status"] = "RUNNING"
    state["runtime_attempt_count"] = int(state.get("runtime_attempt_count", 0)) + 1
    _append_event(
        state,
        "ASTRA_RUNTIME_STARTED",
        attempt=state["runtime_attempt_count"],
        mission_path=task["mission_path"],
    )
    _write_json_atomic(state_path, state)

    env = os.environ.copy()
    env["PROJECT_BRAIN_AGENT_ID"] = agent_id
    env["PROJECT_BRAIN_TASK_ID"] = task["task_id"]
    bridge_dir = (
        root
        / "canonical"
        / "same_identity_worker"
        / "external_tool_bridge"
        / task["task_id"]
    )
    bridge_dir.mkdir(parents=True, exist_ok=True)
    env["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"] = str(bridge_dir)
    argv = [sys.executable, "canonical/runtime/root3_production_astra_launcher_v1.py", task["mission_path"]]
    result = executor(argv, root, env)

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "agent_id": agent_id,
        "task_id": task["task_id"],
        "task_sha256": state["task_sha256"],
        "mission_path": task["mission_path"],
        "mission_sha256": task["mission_sha256"],
        "runtime_command": argv,
        "runtime_returncode": int(result.returncode),
        "stdout_sha256": _sha_text(result.stdout),
        "stderr_sha256": _sha_text(result.stderr),
        "same_identity_bound": (
            env.get("PROJECT_BRAIN_AGENT_ID") == agent_id
            and env.get("PROJECT_BRAIN_TASK_ID") == task["task_id"]
        ),
        "lease_owner": state.get("lease", {}).get("owner"),
        "lease_id_sha256": _sha_text(str(state.get("lease", {}).get("lease_id") or "")),
        "checkpoint_count": int(state.get("checkpoint_count", 0)),
        "runtime_attempt_count": int(state.get("runtime_attempt_count", 0)),
        "incremental_spend_usd": 0,
        "promotion_claim": False,
        "p_real_claim": 0,
    }

    evidence_dir.mkdir(parents=True, exist_ok=True)
    attempt = state["runtime_attempt_count"]
    evidence_path = evidence_dir / f"{task['task_id']}__ATTEMPT_{attempt}.json"
    _write_json_atomic(evidence_path, receipt)

    if result.returncode == 0:
        state["status"] = "COMPLETE"
        _append_event(state, "TASK_COMPLETE", evidence_path=str(evidence_path.relative_to(root)))
    elif result.returncode in {3, 4, 5}:
        state["status"] = "BLOCKED"
        _append_event(
            state,
            "TASK_BLOCKED",
            runtime_returncode=result.returncode,
            evidence_path=str(evidence_path.relative_to(root)),
        )
    else:
        state["status"] = "FAILED"
        _append_event(
            state,
            "TASK_FAILED",
            runtime_returncode=result.returncode,
            evidence_path=str(evidence_path.relative_to(root)),
        )
    state["last_evidence_path"] = str(evidence_path.relative_to(root))
    _write_json_atomic(state_path, state)
    receipt["terminal_state"] = state["status"]
    _write_json_atomic(evidence_path, receipt)
    return int(result.returncode), receipt


def run_once(
    root: pathlib.Path,
    tasks_dir: pathlib.Path,
    state_dir: pathlib.Path,
    evidence_dir: pathlib.Path,
    agent_id: str = DEFAULT_AGENT_ID,
    task_path: pathlib.Path | None = None,
    executor: RuntimeExecutor = _default_executor,
) -> tuple[int, dict[str, Any]]:
    selected = task_path or choose_causally_ready_task(root, tasks_dir, state_dir, agent_id)
    task, _state = claim_task(root, selected, state_dir, agent_id)
    return execute_claimed_task(root, task, state_dir, evidence_dir, agent_id, executor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tasks-dir", default="canonical/same_identity_worker/tasks")
    parser.add_argument("--state-dir", default="canonical/same_identity_worker/state")
    parser.add_argument("--evidence-dir", default="canonical/same_identity_worker/evidence")
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    parser.add_argument("--task")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    tasks_dir = _repo_path(root, args.tasks_dir)
    state_dir = _repo_path(root, args.state_dir)
    evidence_dir = _repo_path(root, args.evidence_dir)
    task_path = _repo_path(root, args.task) if args.task else None
    try:
        code, receipt = run_once(
            root=root,
            tasks_dir=tasks_dir,
            state_dir=state_dir,
            evidence_dir=evidence_dir,
            agent_id=args.agent_id,
            task_path=task_path,
        )
    except NoCausallyReadyTask as exc:
        print(json.dumps({"status": "NO_CAUSALLY_READY_TASK", "error": str(exc)}))
        return 20
    except TaskAlreadyTerminal as exc:
        print(json.dumps({"status": "TASK_ALREADY_TERMINAL", "terminal_state": str(exc)}))
        return 21
    except SupervisorError as exc:
        print(json.dumps({"status": "SUPERVISOR_BLOCKED", "error": str(exc)}))
        return 22
    print(json.dumps(receipt, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
