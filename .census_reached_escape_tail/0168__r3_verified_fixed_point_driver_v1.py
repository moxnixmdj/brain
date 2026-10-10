"""Drive canonical R3 improvement work to a durable fixed point.

No execution, promotion, capability, or terminal authority is created here.
This module only repeats the already-authorized R3 queue transition until the
durable state stops changing or a caller-supplied safety bound is reached.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_R3_VERIFIED_FIXED_POINT_DRIVER_V1"
ROOT = Path(__file__).resolve().parents[2]


class VerifiedFixedPointError(ValueError):
    pass


def _learning_module():
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    return learning


def _queue_driver_module():
    from canonical.runtime import r3_improvement_queue_driver_v1 as queue_driver
    return queue_driver


def _state_sha256(state_path: str | Path) -> str:
    path = Path(state_path)
    if not path.exists():
        return sha256(b"").hexdigest()
    return sha256(path.read_bytes()).hexdigest()


def run(
    *,
    state_path: str | Path | None = None,
    repo_root: str | Path = ROOT,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER"
    ),
    max_rounds: int = 16,
    max_actions_per_round: int = 32,
) -> dict[str, Any]:
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or not 1 <= max_rounds <= 64:
        raise VerifiedFixedPointError("MAX_ROUNDS_INVALID")
    if (
        isinstance(max_actions_per_round, bool)
        or not isinstance(max_actions_per_round, int)
        or not 1 <= max_actions_per_round <= 32
    ):
        raise VerifiedFixedPointError("MAX_ACTIONS_PER_ROUND_INVALID")

    learning = _learning_module()
    queue_driver = _queue_driver_module()
    path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)

    rounds: list[dict[str, Any]] = []
    fixed_point = False
    for index in range(max_rounds):
        before = _state_sha256(path)
        result = queue_driver.drain(
            state_path=path,
            repo_root=repo_root,
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            success_episode_adapter_provider=success_episode_adapter_provider,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=verification_frontier_acquisition_provider,
            verification_frontier_acquisition_provider_id=verification_frontier_acquisition_provider_id,
            max_actions=max_actions_per_round,
        )
        after = _state_sha256(path)
        rounds.append({
            "round": index + 1,
            "state_sha256_before": before,
            "state_sha256_after": after,
            "state_changed": before != after,
            "progress_count": int(result.get("progress_count", 0)),
            "status": result.get("status"),
            "next_improvement_action": deepcopy(result.get("next_improvement_action")),
        })
        if before == after and int(result.get("progress_count", 0)) == 0:
            fixed_point = True
            break

    state = learning.load_state(path)
    next_action = learning.next_improvement_action(state_path=path)
    pending: list[dict[str, Any]] = []
    parked: list[dict[str, Any]] = []
    queue = state.get("improvement_queue", {})
    if isinstance(queue, Mapping):
        for work_id, raw in queue.items():
            if not isinstance(raw, Mapping):
                continue
            row = {"work_id": str(work_id), "kind": raw.get("kind"), "priority": raw.get("priority")}
            if raw.get("status") == "PENDING":
                pending.append(row)
            elif raw.get("status") == "PARKED":
                parked.append(row)

    return {
        "schema": SCHEMA,
        "status": "VERIFIED_R3_FIXED_POINT_REACHED" if fixed_point else "VERIFIED_R3_FIXED_POINT_SAFETY_BOUND_REACHED",
        "pass": fixed_point,
        "fixed_point": fixed_point,
        "round_count": len(rounds),
        "rounds": rounds,
        "pending_work": sorted(pending, key=lambda x: (x.get("priority", 10**9), x["work_id"])),
        "parked_work": sorted(parked, key=lambda x: (x.get("priority", 10**9), x["work_id"])),
        "next_improvement_action": deepcopy(next_action),
        "state_stats": deepcopy(state.get("stats", {})),
        "verification_frontier_acquisition_provider_available": verification_frontier_acquisition_provider is not None,
        "residual_boundary": None if not pending else "CURRENT_R3_WORK_REMAINS_PENDING_OR_PROVIDER_BOUND",
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
