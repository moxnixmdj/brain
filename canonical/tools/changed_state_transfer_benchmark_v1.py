#!/usr/bin/env python3
"""Compare transferred and cold plans on genuinely changed, resettable toy states.

This measures five small, constructed environment families, not arbitrary computer
use. Each target starts from a different state from the source and from the other
target. Both arms start with the same source-only memory snapshot; the cold arm
explicitly disables recall. Plans are executed and checked by ``drive``. Its status
alone does not distinguish direct plan replay from using a prior transition model,
so the returned execution authority is recorded separately.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from transfer_learning_new_environment_probe_20261101 import (  # noqa: E402
    Accum, Grid, Lock, Modulo, Toggles,
)

FAMILIES = {
    "lock": {
        "make": lambda i: Lock((4, 4, 4), (3, 3, 3), [(0, 0, 0), (1, 0, 0), (0, 1, 0)][i]),
        "actions": [f"dial_{i}" for i in range(3)],
        "goal": lambda s: all(v == 3 for v in s),
    },
    "toggles": {
        "make": lambda i: Toggles(4, [bool((i >> bit) & 1) for bit in range(4)]),
        "actions": [f"sw_{i}" for i in range(4)],
        "goal": lambda s: all(s),
    },
    "accumulator": {
        "make": lambda i: Accum("abc", ["", "a", "ab"][i]),
        "actions": ["put_a", "put_b", "put_c"],
        "goal": lambda s: s == "abc",
    },
    "grid": {
        "make": lambda i: Grid((3, 2), [(0, 0), (1, 0), (0, 1)][i]),
        "actions": ["mv_r", "mv_l", "mv_u", "mv_d"],
        "goal": lambda s: s == (3, 2),
    },
    "modulo": {
        "make": lambda i: Modulo(7, 5, i),
        "actions": ["add_1", "add_2", "add_3"],
        "goal": lambda s: s == 5,
    },
}


def _summary(result: dict, elapsed_ms: float) -> dict:
    return {
        "pass": result.get("pass") is True,
        "status": result.get("status"),
        "authority": result.get("authority"),
        "transferred": result.get("transferred"),
        "recall_candidates": result.get("recall_candidates"),
        "candidates_tried": result.get("candidates_tried"),
        "trials": result.get("trials_spent"),
        "action_calls": result.get("interactions", {}).get("act_calls"),
        "elapsed_ms": round(elapsed_ms, 3),
        "plan": result.get("plan"),
    }


def run() -> dict:
    # STATE_PATH is read at import time by transfer_learning_v1. This standalone
    # benchmark imports it only after binding a disposable state file.
    if "canonical.runtime.transfer_learning_v1" in sys.modules:
        raise RuntimeError("BENCHMARK_REQUIRES_FRESH_PROCESS")
    with tempfile.TemporaryDirectory(prefix="brain_changed_state_benchmark_") as temp:
        state = Path(temp) / "episodes.json"
        os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = str(state)
        from canonical.runtime import transfer_learning_v1 as transfer

        families = {}
        for name, spec in FAMILIES.items():
            state.unlink(missing_ok=True)
            starts = [spec["make"](i).state() for i in range(3)]
            if len({repr(start) for start in starts}) != 3:
                raise ValueError(f"INSTANCES_NOT_DISTINCT:{name}")
            if any(spec["goal"](start) for start in starts):
                raise ValueError(f"GOAL_ALREADY_TRUE:{name}")

            def drive(index: int, use_transfer: bool) -> dict:
                started = time.perf_counter()
                result = transfer.drive(
                    spec["make"](index), spec["actions"], is_goal=spec["goal"],
                    goal_key="changed-state-benchmark:" + name, seed=index,
                    budget=200, max_depth=12, use_transfer=use_transfer,
                )
                return _summary(result, (time.perf_counter() - started) * 1000)

            source = drive(0, False)
            if not source["pass"] or not state.is_file():
                raise RuntimeError(f"SOURCE_LESSON_NOT_RETAINED:{name}")
            source_memory = state.read_bytes()
            targets = []
            for index in (1, 2):
                arms = {}
                for arm, enabled in (("cold", False), ("transfer", True)):
                    state.write_bytes(source_memory)
                    arms[arm] = drive(index, enabled)
                targets.append({"initial_state": starts[index], **arms})
            families[name] = {"source_state": starts[0], "source": source, "targets": targets}
        targets = [target for family in families.values() for target in family["targets"]]
        return {
            "schema": "BRAIN_CHANGED_STATE_TRANSFER_BENCHMARK_V1",
            "scope": "five constructed resettable families; source and target states differ",
            "summary": {
                "target_cases": len(targets),
                "cold_solved": sum(row["cold"]["pass"] for row in targets),
                "transfer_solved": sum(row["transfer"]["pass"] for row in targets),
                "direct_plan_replays": sum(
                    row["transfer"]["authority"] == "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED"
                    for row in targets
                ),
            },
            "families": families,
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
