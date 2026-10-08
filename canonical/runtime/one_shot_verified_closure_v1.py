"""One-shot verified closure supervisor.

This is a single invocation wrapper over the canonical R2/R3 machinery. It
executes supplied decision obligations, drains autonomous improvement work to a
fixed point, and returns a truthful residual cut. It never upgrades an internal
missing acquisition/verifier capability into an external-information boundary.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as improvement

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"
ROOT = Path(__file__).resolve().parents[2]

_INTERNAL_BLOCKERS = {
    "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
    "EPISODE_VERIFICATION_PROVIDER_REQUIRED",
    "SKILL_VERIFICATION_PROVIDER_REQUIRED",
    "FAILURE_REPAIR_PROVIDER_REQUIRED",
}


def _pending_rows(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("improvement_queue")
    if not isinstance(raw, Mapping):
        return []
    out = []
    for wid, row in raw.items():
        if isinstance(row, Mapping) and row.get("status") == "PENDING":
            out.append({"work_id": str(wid), **deepcopy(dict(row))})
    return sorted(out, key=lambda r: (int(r.get("priority", 1000)), r["work_id"]))


def _blocker_rows(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = result.get("blockers") or result.get("blockers_skipped") or []
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    return [deepcopy(dict(x)) for x in rows if isinstance(x, Mapping)]


def run(
    *,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
    decision_requests: Sequence[Mapping[str, Any]] = (),
    decision_runner: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id: str = "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER",
    max_rounds: int = 32,
    max_actions_per_round: int = 32,
) -> dict[str, Any]:
    if (
        isinstance(max_rounds, bool)
        or not isinstance(max_rounds, int)
        or not 1 <= max_rounds <= 128
    ):
        raise ValueError("MAX_ROUNDS_INVALID")
    if (
        isinstance(max_actions_per_round, bool)
        or not isinstance(max_actions_per_round, int)
        or not 1 <= max_actions_per_round <= 32
    ):
        raise ValueError("MAX_ACTIONS_PER_ROUND_INVALID")
    if not isinstance(decision_requests, Sequence) or isinstance(decision_requests, (str, bytes)):
        raise ValueError("DECISION_REQUESTS_INVALID")

    decision_results: list[dict[str, Any]] = []
    if decision_requests and decision_runner is None:
        from canonical.runtime import unified_cognitive_fabric_v1 as fabric

        def decision_runner(req):
            wrapped = fabric.run(
                {"mode": "ADEQUATE_DECISION", "payload": deepcopy(dict(req)), "options": {}},
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
                success_episode_adapter_provider=success_episode_adapter_provider,
                verification_frontier_acquisition_provider=verification_frontier_acquisition_provider,
                verification_frontier_acquisition_provider_id=verification_frontier_acquisition_provider_id,
            )
            return wrapped

    for raw in decision_requests:
        if not isinstance(raw, Mapping):
            raise ValueError("DECISION_REQUEST_NOT_OBJECT")
        result = decision_runner(deepcopy(dict(raw)))
        if not isinstance(result, Mapping):
            raise ValueError("DECISION_RUNNER_RESULT_NOT_OBJECT")
        decision_results.append(deepcopy(dict(result)))

    rounds: list[dict[str, Any]] = []
    progress_total = 0
    last: dict[str, Any] = {}
    for index in range(max_rounds):
        result = improvement.drain(
            state_path=state_path,
            repo_root=repo_root,
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            success_episode_adapter_provider=success_episode_adapter_provider,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=verification_frontier_acquisition_provider,
            verification_frontier_acquisition_provider_id=verification_frontier_acquisition_provider_id,
            max_actions=max_actions_per_round,
        )
        if not isinstance(result, Mapping):
            raise ValueError("IMPROVEMENT_DRAIN_RESULT_NOT_OBJECT")
        last = deepcopy(dict(result))
        round_progress = int(result.get("progress_count", 0) or 0)
        progress_total += round_progress
        rounds.append({
            "round": index,
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "progress_count": round_progress,
        })
        if round_progress == 0:
            break

    state = learning.load_state(state_path)
    pending = _pending_rows(state)
    blockers = _blocker_rows(last)
    internal_blockers = [
        row for row in blockers
        if str(row.get("blocker") or "") in _INTERNAL_BLOCKERS
    ]
    frontier_pending = [
        row for row in pending
        if str(row.get("kind") or "") == improvement.FRONTIER_EXPANSION_KIND
    ]
    if frontier_pending and verification_frontier_acquisition_provider is None:
        internal_blockers.extend({
            "work_id": row["work_id"],
            "kind": row.get("kind"),
            "blocker": "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
        } for row in frontier_pending)

    unresolved_decisions = [
        row for row in decision_results
        if row.get("pass") is not True
    ]
    internal_closed = not pending and not unresolved_decisions
    if internal_blockers:
        status = "OPEN__INTERNAL_ACQUISITION_OR_VERIFICATION_CAPABILITY_REQUIRED"
    elif pending:
        status = "FIXED_POINT__PENDING_EVENT_OR_EVIDENCE_WORK_REMAINS"
    elif unresolved_decisions:
        status = "FIXED_POINT__DECISION_RESIDUALS_REMAIN"
    else:
        status = "PASS__CURRENT_INTERNAL_ACTIONABLE_FRONTIER_EMPTY"

    return {
        "schema": SCHEMA,
        "status": status,
        "pass": internal_closed,
        "internal_actionable_frontier_empty": internal_closed,
        "round_count": len(rounds),
        "progress_count": progress_total,
        "rounds": rounds,
        "decision_results": decision_results,
        "pending_work": pending,
        "internal_blockers": internal_blockers,
        "unresolved_decision_count": len(unresolved_decisions),
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "open_world_completion_claimed": False,
    }
