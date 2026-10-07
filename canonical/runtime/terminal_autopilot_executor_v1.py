from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from canonical.runtime import same_identity_supervisor
from canonical.runtime import terminal_autopilot_v1

SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTOPILOT_EXECUTOR_V1"
TASK_SCHEMA = "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1"
TASKS_DIR = "canonical/same_identity_worker/tasks"
STATE_DIR = "canonical/same_identity_worker/state"
EVIDENCE_DIR = "canonical/same_identity_worker/evidence"

SAFE_CLASSES = {
    "EXECUTE": {"REVERSIBLE_ZERO_REALITY"},
    "VERIFY": {"INDEPENDENT_ZERO_SPEND_VERIFY"},
    "PROMOTE": {"CONTENT_BOUND_PROMOTION"},
}
PHASE_RANK = {"EXECUTE": 1, "VERIFY": 2, "PROMOTE": 3}


class AutopilotExecutionError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AutopilotExecutionError("JSON_OBJECT_REQUIRED")
    return value


def _repo_path(root: Path, value: str) -> Path:
    root = root.resolve()
    path = (root / value).resolve()
    if path == root or root not in path.parents:
        raise AutopilotExecutionError("PATH_OUTSIDE_REPOSITORY")
    return path


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _action_targets(action: dict[str, Any]) -> list[str]:
    ids = action.get("obligation_ids")
    if isinstance(ids, list):
        return sorted(x for x in ids if isinstance(x, str) and x)
    unlocks = action.get("unlocks")
    if isinstance(unlocks, list):
        return sorted(x for x in unlocks if isinstance(x, str) and x)
    return []


def _plan_actions(plan_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if plan_doc.get("pass") is not True:
        raise AutopilotExecutionError("AUTOPILOT_PLAN_NOT_PASSING")
    rows: list[dict[str, Any]] = []
    for key in ("dispatch", "verify", "promote"):
        value = plan_doc.get(key, [])
        if not isinstance(value, list):
            raise AutopilotExecutionError("PLAN_ACTION_COLLECTION_INVALID:" + key)
        rows.extend(x for x in value if isinstance(x, dict))
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        action_id = row.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise AutopilotExecutionError("PLAN_ACTION_ID_INVALID")
        if action_id in out:
            raise AutopilotExecutionError("DUPLICATE_PLAN_ACTION:" + action_id)
        out[action_id] = row
    return out


def _task_gate(root: Path, task: dict[str, Any]) -> dict[str, Any]:
    if task.get("schema") != TASK_SCHEMA:
        raise AutopilotExecutionError("TASK_SCHEMA_INVALID")
    if float(task.get("incremental_spend_usd", 0)) != 0.0:
        raise AutopilotExecutionError("NONZERO_INCREMENTAL_SPEND")
    meta = task.get("terminal_autopilot")
    if not isinstance(meta, dict) or meta.get("enabled") is not True:
        raise AutopilotExecutionError("AUTOPILOT_NOT_EXPLICITLY_ENABLED")
    phase = str(meta.get("phase") or "").upper()
    if phase not in SAFE_CLASSES:
        raise AutopilotExecutionError("AUTOPILOT_PHASE_INVALID")
    execution_class = str(meta.get("execution_class") or "")
    if execution_class not in SAFE_CLASSES[phase]:
        raise AutopilotExecutionError("AUTOPILOT_EXECUTION_CLASS_NOT_AUTHORIZED")
    if meta.get("irreversible_benchmark") is True:
        raise AutopilotExecutionError("IRREVERSIBLE_BENCHMARK_AUTOEXECUTION_FORBIDDEN")
    action_id = str(meta.get("action_id") or "")
    if not action_id:
        raise AutopilotExecutionError("AUTOPILOT_ACTION_ID_REQUIRED")
    obligation_ids = meta.get("obligation_ids")
    if (
        not isinstance(obligation_ids, list)
        or not obligation_ids
        or not all(isinstance(x, str) and x for x in obligation_ids)
    ):
        raise AutopilotExecutionError("AUTOPILOT_OBLIGATION_IDS_INVALID")

    if phase == "PROMOTE":
        authority = meta.get("promotion_authority")
        if not isinstance(authority, dict):
            raise AutopilotExecutionError("PROMOTION_AUTHORITY_REQUIRED")
        rel = authority.get("path")
        expected = authority.get("git_blob_sha")
        if not isinstance(rel, str) or not rel or not isinstance(expected, str) or len(expected) != 40:
            raise AutopilotExecutionError("PROMOTION_AUTHORITY_BINDING_INVALID")
        p = _repo_path(root, rel)
        if not p.is_file() or _git_blob_sha(p.read_bytes()) != expected.lower():
            raise AutopilotExecutionError("PROMOTION_AUTHORITY_BYTE_MISMATCH")

    return {
        "phase": phase,
        "phase_rank": PHASE_RANK[phase],
        "execution_class": execution_class,
        "action_id": action_id,
        "obligation_ids": sorted(set(obligation_ids)),
        "agent_id": str(task.get("agent_id") or ""),
        "task_id": str(task.get("task_id") or ""),
    }


def _load_worker_state(state_dir: Path, task_id: str) -> dict[str, Any] | None:
    p = state_dir / (task_id + ".json")
    if not p.is_file():
        return None
    try:
        return _read_json(p)
    except Exception:
        return {"status": "INVALID"}


def overlay_worker_progress(
    manifest: dict[str, Any],
    root: str | Path,
    *,
    tasks_dir: str = TASKS_DIR,
    state_dir: str = STATE_DIR,
) -> dict[str, Any]:
    root = Path(root).resolve()
    tasks = _repo_path(root, tasks_dir)
    states = _repo_path(root, state_dir)
    by_id = {
        row.get("id"): row
        for row in manifest.get("obligations", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    best_rank: dict[str, int] = {}
    best_status: dict[str, str] = {}

    if tasks.is_dir():
        for path in sorted(tasks.glob("*.json")):
            try:
                task = _read_json(path)
                meta = _task_gate(root, task)
            except Exception:
                continue
            state = _load_worker_state(states, meta["task_id"])
            if not state:
                continue
            status = state.get("status")
            if status in {"CLAIMED", "RUNNING", "CHECKPOINTED_RELAUNCH_REQUIRED"}:
                for oid in meta["obligation_ids"]:
                    if oid in by_id and by_id[oid].get("status") not in {"CLOSED", "PROMOTED"}:
                        by_id[oid]["status"] = "RUNNING"
                continue
            if status != "COMPLETE":
                continue
            if meta["phase"] == "EXECUTE":
                projected = "RESULT_PRESENT"
            elif meta["phase"] == "VERIFY":
                projected = "VERIFIED"
            else:
                # Promotion completion must change canonical truth itself; executor
                # state is never sufficient to mint PROMOTED.
                continue
            for oid in meta["obligation_ids"]:
                if oid not in by_id or by_id[oid].get("status") in {"CLOSED", "PROMOTED"}:
                    continue
                rank = meta["phase_rank"]
                if rank > best_rank.get(oid, 0):
                    best_rank[oid] = rank
                    best_status[oid] = projected

    for oid, status in best_status.items():
        by_id[oid]["status"] = status
    return manifest


def build_plan_from_repo(
    repo_root: str | Path,
    *,
    max_concurrency: int = 16,
    tasks_dir: str = TASKS_DIR,
    state_dir: str = STATE_DIR,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = terminal_autopilot_v1.build_manifest_from_repo(
        repo_root, max_concurrency=max_concurrency
    )
    overlay_worker_progress(
        manifest, repo_root, tasks_dir=tasks_dir, state_dir=state_dir
    )
    return manifest, terminal_autopilot_v1.plan(manifest)


def select_runnable_tasks(
    repo_root: str | Path,
    plan_doc: dict[str, Any],
    *,
    tasks_dir: str = TASKS_DIR,
    state_dir: str = STATE_DIR,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    tasks = _repo_path(root, tasks_dir)
    states = _repo_path(root, state_dir)
    actions = _plan_actions(plan_doc)
    candidates: list[dict[str, Any]] = []

    if not tasks.is_dir():
        return []
    for path in sorted(tasks.glob("*.json")):
        try:
            task = _read_json(path)
            meta = _task_gate(root, task)
        except Exception:
            continue
        planned = actions.get(meta["action_id"])
        if planned is None:
            continue
        expected_targets = _action_targets(planned)
        if expected_targets and meta["obligation_ids"] != expected_targets:
            continue
        state = _load_worker_state(states, meta["task_id"])
        if state and state.get("status") in {
            "COMPLETE", "FAILED", "BLOCKED", "CLAIMED", "RUNNING"
        }:
            continue
        candidates.append({
            "path": str(path),
            "task": task,
            "meta": meta,
            "plan_action": planned,
        })

    # One concurrent task per durable worker identity. Across identities, fan out.
    # Higher phase rank first so already-produced evidence verifies/promotes before
    # opening redundant new work.
    candidates.sort(
        key=lambda x: (
            -x["meta"]["phase_rank"],
            x["meta"]["action_id"],
            x["meta"]["task_id"],
        )
    )
    selected: list[dict[str, Any]] = []
    agents: set[str] = set()
    actions_seen: set[str] = set()
    for item in candidates:
        agent = item["meta"]["agent_id"]
        action = item["meta"]["action_id"]
        if not agent or agent in agents or action in actions_seen:
            continue
        agents.add(agent)
        actions_seen.add(action)
        selected.append(item)
    return selected


Runner = Callable[..., tuple[int, dict[str, Any]]]


def execute_wave(
    repo_root: str | Path,
    plan_doc: dict[str, Any],
    *,
    max_concurrency: int = 16,
    tasks_dir: str = TASKS_DIR,
    state_dir: str = STATE_DIR,
    evidence_dir: str = EVIDENCE_DIR,
    runner: Runner = same_identity_supervisor.run_once,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = select_runnable_tasks(
        root, plan_doc, tasks_dir=tasks_dir, state_dir=state_dir
    )[:max_concurrency]
    if not selected:
        return {
            "schema": SCHEMA,
            "status": "QUIESCENT",
            "selected": [],
            "results": [],
            "terminal_credit": False,
        }

    task_dir_path = _repo_path(root, tasks_dir)
    state_dir_path = _repo_path(root, state_dir)
    evidence_dir_path = _repo_path(root, evidence_dir)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(max_concurrency, len(selected)))) as pool:
        futures = {}
        for item in selected:
            fut = pool.submit(
                runner,
                root=root,
                tasks_dir=task_dir_path,
                state_dir=state_dir_path,
                evidence_dir=evidence_dir_path,
                agent_id=item["meta"]["agent_id"],
                task_path=Path(item["path"]),
            )
            futures[fut] = item
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                code, receipt = fut.result()
                results.append({
                    "task_id": item["meta"]["task_id"],
                    "action_id": item["meta"]["action_id"],
                    "phase": item["meta"]["phase"],
                    "returncode": int(code),
                    "receipt": receipt,
                })
            except Exception as exc:
                results.append({
                    "task_id": item["meta"]["task_id"],
                    "action_id": item["meta"]["action_id"],
                    "phase": item["meta"]["phase"],
                    "returncode": None,
                    "error": type(exc).__name__ + ":" + str(exc),
                })

    results.sort(key=lambda x: (x["action_id"], x["task_id"]))
    return {
        "schema": SCHEMA,
        "status": "WAVE_COMPLETE",
        "selected": [x["meta"]["task_id"] for x in selected],
        "results": results,
        "terminal_credit": False,
        "rule": (
            "REVERSIBLE_ZERO_REALITY_AND_INDEPENDENT_VERIFY_ONLY_BY_DEFAULT__"
            "PROMOTION_REQUIRES_EXACT_CONTENT_BOUND_AUTHORITY__"
            "IRREVERSIBLE_BENCHMARK_AUTOEXECUTION_FORBIDDEN"
        ),
    }


def run_until_quiescent(
    repo_root: str | Path,
    *,
    max_concurrency: int = 16,
    max_waves: int = 32,
    runner: Runner = same_identity_supervisor.run_once,
) -> dict[str, Any]:
    waves = []
    for _ in range(max_waves):
        _manifest, plan_doc = build_plan_from_repo(
            repo_root, max_concurrency=max_concurrency
        )
        wave = execute_wave(
            repo_root,
            plan_doc,
            max_concurrency=max_concurrency,
            runner=runner,
        )
        waves.append(wave)
        if wave["status"] == "QUIESCENT":
            return {
                "schema": SCHEMA,
                "status": "QUIESCENT",
                "waves": waves,
                "terminal_credit": False,
            }
    return {
        "schema": SCHEMA,
        "status": "MAX_WAVES_REACHED_FAIL_CLOSED",
        "waves": waves,
        "terminal_credit": False,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    result = run_until_quiescent(root)
    print(json.dumps(result, indent=2, sort_keys=True))
