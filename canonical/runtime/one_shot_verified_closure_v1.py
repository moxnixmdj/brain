"""One-shot verified closure supervisor.

This module composes the existing R3 queue driver into a fixed-point operation.
It grants no new verification, promotion, terminal, or external-reality authority.

The operation stops only when one of these conditions is proved on the current
state/provider frontier:
1. the improvement queue is empty;
2. every remaining work item is non-actionable and the residual class is typed;
3. a claimed-progress invariant is violated, in which case it fails closed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as r3

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"

LOAD_BEARING_PATHS = (
    "canonical/runtime/autonomous_verified_self_improvement_v1.py",
    "canonical/runtime/r3_improvement_queue_driver_v1.py",
    "canonical/runtime/live_brain_runtime_v1.py",
    "canonical/runtime/unified_cognitive_fabric_v1.py",
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
)

INTERNAL_ROOT1_BLOCKERS = {
    "ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP__NO_BOUND_ACQUISITION_ROUTE",
    "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
}

EXTERNAL_OR_NEW_EVIDENCE_BLOCKERS = {
    "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
    "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
    "FRONTIER_ACQUISITION_ALREADY_ATTEMPTED_FOR_CURRENT_PROVIDER_AND_FRONTIER",
}


class OneShotClosureError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _safe_file_digest(root: Path, relative: str) -> dict[str, Any]:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise OneShotClosureError("LOAD_BEARING_PATH_INVALID:" + relative)
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    return {
        "path": relative,
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def frontier_snapshot(
    *,
    repo_root: str | Path,
    state_path: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    pending: list[dict[str, Any]] = []
    if isinstance(queue, Mapping):
        for wid, raw in queue.items():
            if not isinstance(raw, Mapping):
                continue
            if raw.get("status") not in {"PENDING", "PARKED"}:
                continue
            pending.append({
                "work_id": str(wid),
                "kind": str(raw.get("kind") or ""),
                "status": str(raw.get("status") or ""),
                "observations": int(raw.get("observations", 0)),
                "last_attempt_observations": raw.get("last_attempt_observations"),
                "last_attempt_provider_id": raw.get("last_attempt_provider_id"),
                "last_attempt_frontier_sha256": raw.get(
                    "last_attempt_frontier_sha256"
                ),
            })
    files = [_safe_file_digest(root, rel) for rel in LOAD_BEARING_PATHS]
    payload = {
        "files": files,
        "pending": sorted(pending, key=lambda x: (x["kind"], x["work_id"])),
        "stats": deepcopy(state.get("stats", {})),
    }
    return {
        "schema": SCHEMA,
        "digest": _sha(payload),
        "payload": payload,
    }


def _extract_blockers(actions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions:
        candidates = []
        if isinstance(action.get("blockers"), list):
            candidates.extend(action.get("blockers") or [])
        if isinstance(action.get("blockers_skipped"), list):
            candidates.extend(action.get("blockers_skipped") or [])
        for raw in candidates:
            if not isinstance(raw, Mapping):
                continue
            row = {
                "work_id": str(raw.get("work_id") or ""),
                "kind": str(raw.get("kind") or ""),
                "blocker": str(raw.get("blocker") or ""),
                "boundary_root": raw.get("boundary_root"),
                "required_capability_class": raw.get("required_capability_class"),
                "root1_positive_gap_established": (
                    raw.get("root1_positive_gap_established") is True
                ),
            }
            key = _sha(row)
            if key not in seen:
                seen.add(key)
                out.append(row)
    return out


def classify_residual(blockers: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not blockers:
        return {
            "class": "NONE",
            "internally_solvable_gap_remaining": False,
            "external_or_new_evidence_required": False,
        }
    names = {str(row.get("blocker") or "") for row in blockers}
    internal = sorted(names & INTERNAL_ROOT1_BLOCKERS)
    unsupported = sorted(
        name
        for name in names
        if name
        and name not in INTERNAL_ROOT1_BLOCKERS
        and name not in EXTERNAL_OR_NEW_EVIDENCE_BLOCKERS
    )
    waiting = sorted(names & EXTERNAL_OR_NEW_EVIDENCE_BLOCKERS)
    if internal:
        cls = "INTERNAL_ROOT1_CONSTRUCTIVE_CAPABILITY_GAP"
    elif unsupported:
        cls = "INTERNAL_UNCLASSIFIED_OR_UNSUPPORTED_GAP"
    else:
        cls = "EXTERNAL_OR_NEW_EVIDENCE_REQUIRED"
    return {
        "class": cls,
        "internally_solvable_gap_remaining": bool(internal or unsupported),
        "external_or_new_evidence_required": bool(waiting) and not bool(
            internal or unsupported
        ),
        "internal_blockers": internal,
        "unsupported_blockers": unsupported,
        "evidence_blockers": waiting,
    }


def run(
    *,
    repo_root: str | Path,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "ONE_SHOT_ROOT1_ACQUISITION_PROVIDER"
    ),
    failure_repair_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ] | None = None,
    max_rounds: int = 64,
    max_actions_per_round: int = 32,
) -> dict[str, Any]:
    if (
        isinstance(max_rounds, bool)
        or not isinstance(max_rounds, int)
        or max_rounds < 1
        or max_rounds > 512
    ):
        raise OneShotClosureError("MAX_ROUNDS_INVALID")
    if (
        isinstance(max_actions_per_round, bool)
        or not isinstance(max_actions_per_round, int)
        or max_actions_per_round < 1
        or max_actions_per_round > 32
    ):
        raise OneShotClosureError("MAX_ACTIONS_PER_ROUND_INVALID")

    transcript: list[dict[str, Any]] = []
    initial = frontier_snapshot(repo_root=repo_root, state_path=state_path)
    final = initial
    final_blockers: list[dict[str, Any]] = []

    for round_index in range(max_rounds):
        before = frontier_snapshot(repo_root=repo_root, state_path=state_path)
        drained = r3.drain(
            state_path=state_path,
            repo_root=repo_root,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=(
                verification_frontier_acquisition_provider
            ),
            verification_frontier_acquisition_provider_id=(
                verification_frontier_acquisition_provider_id
            ),
            max_actions=max_actions_per_round,
        )
        after = frontier_snapshot(repo_root=repo_root, state_path=state_path)
        actions = [
            deepcopy(dict(x))
            for x in (drained.get("actions") or [])
            if isinstance(x, Mapping)
        ]
        blockers = _extract_blockers(actions)
        changed = before["digest"] != after["digest"]
        claimed_progress = int(drained.get("progress_count", 0)) > 0

        if claimed_progress and not changed:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__CLAIMED_PROGRESS_WITHOUT_STATE_OR_FRONTIER_CHANGE",
                "pass": False,
                "fixed_point": False,
                "round": round_index,
                "initial_frontier_digest": initial["digest"],
                "before_frontier_digest": before["digest"],
                "after_frontier_digest": after["digest"],
                "drain_result": deepcopy(dict(drained)),
                "terminal_authority": False,
            }

        transcript.append({
            "round": round_index,
            "before_frontier_digest": before["digest"],
            "after_frontier_digest": after["digest"],
            "frontier_changed": changed,
            "progress_count": int(drained.get("progress_count", 0)),
            "status": drained.get("status"),
            "blockers": blockers,
        })
        final = after
        final_blockers = blockers

        pending = after["payload"]["pending"]
        if not pending:
            return {
                "schema": SCHEMA,
                "status": "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
                "pass": True,
                "fixed_point": True,
                "closure_class": "NO_CURRENT_INTERNAL_IMPROVEMENT_WORK_REMAINS",
                "initial_frontier_digest": initial["digest"],
                "final_frontier_digest": after["digest"],
                "rounds_executed": round_index + 1,
                "transcript": transcript,
                "residual": classify_residual([]),
                "terminal_authority": False,
            }

        if not changed and int(drained.get("progress_count", 0)) == 0:
            residual = classify_residual(blockers)
            internal = residual["internally_solvable_gap_remaining"]
            return {
                "schema": SCHEMA,
                "status": (
                    "OPEN__INTERNAL_SOLVABLE_GAP_REMAINS"
                    if internal
                    else "VERIFIED_FIXED_POINT__EXTERNAL_OR_NEW_EVIDENCE_REQUIRED"
                ),
                "pass": not internal,
                "fixed_point": True,
                "closure_class": residual["class"],
                "initial_frontier_digest": initial["digest"],
                "final_frontier_digest": after["digest"],
                "rounds_executed": round_index + 1,
                "transcript": transcript,
                "residual": residual,
                "terminal_authority": False,
            }

    residual = classify_residual(final_blockers)
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__MAX_ROUNDS_REACHED_BEFORE_FIXED_POINT",
        "pass": False,
        "fixed_point": False,
        "initial_frontier_digest": initial["digest"],
        "final_frontier_digest": final["digest"],
        "rounds_executed": max_rounds,
        "transcript": transcript,
        "residual": residual,
        "terminal_authority": False,
    }
