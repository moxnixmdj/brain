#!/usr/bin/env python3
"""Fail-closed consistency reducer for Project Brain frontier state.

This reducer checks cross-surface invariants without pinning transient frontier
facts such as a specific cut version, observation count, or cost. It is intended
to remain valid as the frontier legitimately advances.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def verify() -> dict[str, Any]:
    h = load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    u = load("canonical/governance/RESIDUAL_ACTION_UNIVERSE_V2.json")
    p = load("canonical/CANONICAL_POINTER.json")
    s = load("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")
    policy = load("canonical/governance/ATOMIC_FRONTIER_TRANSACTION_V1.json")

    failures: list[dict[str, Any]] = []

    def eq(name: str, left: Any, right: Any) -> None:
        if left != right:
            failures.append({"invariant": name, "left": left, "right": right})

    blocker = h["current_parent_blocker"]
    next_action = h["next_required_action_class"]
    active = s["active_frontier_accounting"]
    mirror = h["residual_action_universe_v2"]

    eq("pointer.critical_blocker", p["current_frontier"]["critical_blocker"], blocker)
    eq(
        "pointer.highest_leverage_capability_gap",
        p["current_frontier"]["highest_leverage_capability_gap"],
        blocker,
    )
    eq("pointer.next_step", p["current_frontier"]["next_step"], next_action)

    eq("scoreboard.residual_gap", active["residual_gap"], blocker)
    eq("scoreboard.current_parent_blocker", active["current_parent_blocker"], blocker)
    eq("scoreboard.next_required_action", active["next_required_action"], next_action)
    eq("scoreboard.top_level_next_required_action", s["next_required_action"], next_action)
    eq(
        "scoreboard.next_progress_event_target",
        s["next_progress_event_target"],
        h["next_progress_event_target"],
    )

    eq("residual.status", mirror["status"], u["status"])
    eq("residual.exact_cut_ready", mirror["exact_cut_ready"], u["exact_cut_ready"])
    eq(
        "residual.blocking_obligations",
        mirror["blocking_obligations"],
        u["blocking_obligations"],
    )

    if bool(u["exact_cut_ready"]) and u["blocking_obligations"]:
        failures.append(
            {
                "invariant": "exact_cut_ready_implies_no_blocking_obligations",
                "blocking_obligations": u["blocking_obligations"],
            }
        )

    boot = p["boot_requirements"]
    if boot.get("atomic_frontier_transaction_required") is not True:
        failures.append({"invariant": "atomic_frontier_transaction_required"})
    eq(
        "atomic_frontier_transaction_policy_path",
        boot.get("atomic_frontier_transaction_policy_path"),
        "canonical/governance/ATOMIC_FRONTIER_TRANSACTION_V1.json",
    )
    if policy.get("status") != "CANONICAL_ACTIVE":
        failures.append(
            {
                "invariant": "atomic_frontier_transaction_policy_active",
                "status": policy.get("status"),
            }
        )

    latency = h.get("execution_latency_control", {})
    if latency.get("status") != "ACTIVE":
        failures.append(
            {
                "invariant": "execution_latency_control_active",
                "status": latency.get("status"),
            }
        )

    result = {
        "schema": "PROJECT_BRAIN_FRONTIER_STATE_CONSISTENCY_V1",
        "status": "PASS" if not failures else "FAIL_CLOSED",
        "frontier_blocker": blocker,
        "exact_cut_ready": bool(u["exact_cut_ready"]),
        "blocking_obligations": u["blocking_obligations"],
        "failures": failures,
    }
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
