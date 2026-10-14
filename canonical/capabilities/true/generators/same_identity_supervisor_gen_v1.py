"""Fresh-instance generator for SAME_IDENTITY_SUPERVISOR_V1.

An instance is a small *world* (task manifests, mission files, prerequisite files)
plus a *script* of supervisor operations issued by two identities: the durable
worker ("self") and an intruder ("other").  The script mixes legitimate work with
adversarial events: wrong-identity claims, manifest edits (priority, agent id),
mission edits, prerequisite edits/deletions, and direct execute calls on tasks
in every state.  Nothing here imports the supervisor; the manifest schema string
is the published contract.
"""
from __future__ import annotations

import hashlib
import json
import random

TASK_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1"
BLOCKED_CODES = (3, 4, 5)
FAIL_CODES = (1, 2, 7, 9, 70, 137)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hex(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _wrong_sha(rng: random.Random, right: str) -> str:
    while True:
        cand = _hex(rng, 64)
        if cand != right:
            return cand


def _instance(rng: random.Random) -> dict:
    self_agent = "AGENT-" + _hex(rng, 8).upper()
    other_agent = "INTRUDER-" + _hex(rng, 8).upper()
    files: dict[str, str] = {}

    # prerequisite file pool: some exist, some are referenced but never written
    dep_count = rng.randint(2, 5)
    deps = []
    for j in range(dep_count):
        path = f"deps/d{j}_{_hex(rng, 4)}.txt"
        exists = rng.random() < 0.8
        content = f"dep {j} {_hex(rng, 12)}\n"
        if exists:
            files[path] = content
        deps.append({"path": path, "exists": exists, "content": content})

    tasks = []
    task_count = rng.randint(2, 5)
    used_ids: set[str] = set()
    for k in range(task_count):
        while True:
            task_id = f"T{k}-{_hex(rng, 6)}"
            if task_id not in used_ids:
                used_ids.add(task_id)
                break
        mission_path = f"missions/{task_id}.json"
        mission_text = json.dumps({"mission_id": task_id, "payload": _hex(rng, 16), "steps": rng.randint(1, 9)}) + "\n"
        files[mission_path] = mission_text
        right = _sha(mission_text)
        mission_sha = right if rng.random() < 0.9 else _wrong_sha(rng, right)
        prereqs: list = []
        for dep in rng.sample(deps, k=rng.randint(0, min(3, len(deps)))):
            if rng.random() < 0.5:
                prereqs.append(dep["path"])
            else:
                good = _sha(dep["content"])
                prereqs.append({"path": dep["path"], "sha256": good if rng.random() < 0.85 else _wrong_sha(rng, good)})
        manifest = {
            "schema": TASK_SCHEMA if rng.random() < 0.96 else "PROJECT_BRAIN_SOME_OTHER_SCHEMA",
            "task_id": task_id,
            "agent_id": self_agent if rng.random() < 0.88 else other_agent,
            "mission_path": mission_path,
            "mission_sha256": mission_sha,
            "priority": rng.randint(0, 1000),
            "prerequisites": prereqs,
            "incremental_spend_usd": 0 if rng.random() < 0.95 else rng.choice([0.5, 1, 12.5]),
            "checkpoint_before_runtime_once": rng.random() < 0.3,
        }
        tasks.append({"task_id": task_id, "manifest_path": f"tasks/{task_id}.json", "manifest": manifest})

    def _rc() -> int:
        r = rng.random()
        if r < 0.4:
            return 0
        if r < 0.65:
            return rng.choice(BLOCKED_CODES)
        return rng.choice(FAIL_CODES)

    def _agent() -> str:
        return "self" if rng.random() < 0.85 else "other"

    script: list[dict] = []
    for _ in range(rng.randint(6, 16)):
        r = rng.random()
        i = rng.randrange(task_count)
        if r < 0.18:
            script.append({"op": "choose"})
        elif r < 0.48:
            script.append({"op": "run", "task": i, "agent": _agent(), "rc": _rc()})
        elif r < 0.62:
            script.append({"op": "claim", "task": i, "agent": _agent()})
        elif r < 0.76:
            script.append({"op": "execute", "task": i, "agent": _agent(), "rc": _rc()})
        elif r < 0.84:
            script.append({"op": "edit_manifest", "task": i, "field": "priority", "value": rng.randint(0, 1000)})
        elif r < 0.89:
            script.append({"op": "edit_manifest", "task": i, "field": "agent_id",
                           "value": other_agent if rng.random() < 0.7 else self_agent})
        elif r < 0.94:
            script.append({"op": "edit_file", "path": tasks[i]["manifest"]["mission_path"],
                           "content": json.dumps({"mission_id": tasks[i]["task_id"], "payload": _hex(rng, 16)}) + "\n"})
        else:
            dep = rng.choice(deps)
            if rng.random() < 0.5:
                script.append({"op": "edit_file", "path": dep["path"], "content": f"changed {_hex(rng, 10)}\n"})
            else:
                script.append({"op": "delete_file", "path": dep["path"]})
    if rng.random() < 0.4:
        # deliberate takeover attempt: the worker leases a task, the manifest is rewritten to
        # name the intruder, the intruder tries every entry point, then the manifest is restored
        i = rng.randrange(task_count)
        takeover = [
            {"op": "run", "task": i, "agent": "self", "rc": rng.choice(BLOCKED_CODES)},
            {"op": "edit_manifest", "task": i, "field": "agent_id", "value": other_agent},
            {"op": "claim", "task": i, "agent": "other"},
            {"op": "execute", "task": i, "agent": "other", "rc": _rc()},
            {"op": "run", "task": i, "agent": "other", "rc": _rc()},
            {"op": "edit_manifest", "task": i, "field": "agent_id", "value": self_agent},
            {"op": "run", "task": i, "agent": "self", "rc": _rc()},
        ]
        at = rng.randint(0, len(script))
        script[at:at] = takeover
    return {
        "schema": "SAME_IDENTITY_SUPERVISOR_INSTANCE_V1",
        "agent_id": self_agent,
        "other_agent_id": other_agent,
        "files": files,
        "tasks": tasks,
        "script": script,
    }


def generate(rng: random.Random, n: int) -> list[dict]:
    return [_instance(rng) for _ in range(n)]
