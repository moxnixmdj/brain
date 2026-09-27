#!/usr/bin/env python3
"""Bounded same-identity execution loop with a separate external-tool relay."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

import external_tool_relay as relay


ROOT = pathlib.Path(__file__).resolve().parents[2]


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_loop(
    *,
    task_path: pathlib.Path,
    agent_id: str,
    task_id: str,
    allow_hosts: set[str],
    max_rounds: int,
    max_body_bytes: int,
) -> dict:
    bridge_dir = (
        ROOT / "canonical" / "same_identity_worker" / "external_tool_bridge" / task_id
    )
    task_path = task_path.resolve()
    attempts = []
    relay_events = []

    for round_index in range(1, max_rounds + 1):
        proc = subprocess.run(
            [
                sys.executable,
                "canonical/runtime/same_identity_supervisor.py",
                "--agent-id", agent_id,
                "--task", str(task_path.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        event = {
            "round": round_index,
            "returncode": proc.returncode,
            "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
        attempts.append(event)
        print(json.dumps({"supervisor": event}, sort_keys=True), flush=True)

        if proc.returncode == 0:
            state_path = (
                ROOT / "canonical" / "same_identity_worker" / "state" /
                (task_id + ".json")
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("status") != "COMPLETE":
                raise RuntimeError("SUPERVISOR_ZERO_WITHOUT_COMPLETE_STATE")
            return {
                "schema": "PROJECT_BRAIN_SAME_IDENTITY_RELAY_LOOP_V1",
                "status": "COMPLETE",
                "agent_id": agent_id,
                "task_id": task_id,
                "rounds": round_index,
                "attempts": attempts,
                "relay_events": relay_events,
                "task_sha256": _sha(task_path),
                "state_sha256": _sha(state_path),
            }

        # 75 is the supervisor's intentional checkpoint/relaunch signal.
        if proc.returncode == 75:
            continue

        service = relay.service_pending(
            bridge_dir,
            allowed_hosts=allow_hosts,
            agent_id=agent_id,
            task_id=task_id,
            max_body_bytes=max_body_bytes,
        )
        relay_events.append({"round": round_index, **service})
        print(json.dumps({"relay": relay_events[-1]}, sort_keys=True), flush=True)

        if int(service.get("pending_serviced", 0)) > 0:
            continue

        # No pending bridge work means reality exposed a different blocker.
        return {
            "schema": "PROJECT_BRAIN_SAME_IDENTITY_RELAY_LOOP_V1",
            "status": "NEW_BLOCKER",
            "agent_id": agent_id,
            "task_id": task_id,
            "rounds": round_index,
            "returncode": proc.returncode,
            "attempts": attempts,
            "relay_events": relay_events,
            "task_sha256": _sha(task_path),
        }

    return {
        "schema": "PROJECT_BRAIN_SAME_IDENTITY_RELAY_LOOP_V1",
        "status": "ROUND_LIMIT",
        "agent_id": agent_id,
        "task_id": task_id,
        "rounds": max_rounds,
        "attempts": attempts,
        "relay_events": relay_events,
        "task_sha256": _sha(task_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--allow-host", action="append", required=True)
    parser.add_argument("--max-rounds", type=int, default=24)
    parser.add_argument("--max-body-bytes", type=int, default=50_000_000)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    task_path = (ROOT / args.task).resolve()
    if ROOT not in task_path.parents:
        raise RuntimeError("TASK_PATH_OUTSIDE_ROOT")
    if args.max_rounds <= 0 or args.max_rounds > 64:
        raise RuntimeError("ROUND_LIMIT_OUT_OF_RANGE")

    result = run_loop(
        task_path=task_path,
        agent_id=args.agent_id,
        task_id=args.task_id,
        allow_hosts={h.rstrip(".").lower() for h in args.allow_host},
        max_rounds=args.max_rounds,
        max_body_bytes=args.max_body_bytes,
    )
    summary = (ROOT / args.summary).resolve()
    if ROOT not in summary.parents:
        raise RuntimeError("SUMMARY_PATH_OUTSIDE_ROOT")
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
