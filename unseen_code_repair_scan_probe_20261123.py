#!/usr/bin/env python3
"""Unseen-content probe for the CODE-REPAIR direction via the GENERIC scan (§23).

The §17 generic loop honestly refused code-repair goals (no plan after scan).
This probe drives that SAME generic loop through the corrected, real-file env
(canonical/swe_kernel/code_repair_scan_env_v1.py):

  TEACH  broken module + real failing test -> cold scan -> plan -> ACT -> VERIFY
         -> admit on two fresh variants -> persist the rule
  COLD   fresh broken file (different content, same shape) -> cold scan
  WARM   same fresh broken file, memory seeded by TEACH
         -> rule replay (instant) or carried-model walk or rescan
  CONTROL  the TEACH content re-run with TEACH memory (is the instant path real?)

Fresh variants for admission (same goal family, unseen content):
  A - diff(x, y) = x - y, test asserts diff(2, 3) == 5   (same defect; rule transfers)
  B - scale(x, y) = x - y, test asserts scale(10, 2) == 8 (already correct under its
      own contract; the rule must not break it)

Authority NONE. Producer-run sandbox measurement. No capability registered.
No model calls, no network, $0.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.code_repair_scan_env_v1 import (
    build_code_repair_env,
    DEFAULT_CANDIDATES,
)

GOAL = "fix module.py so its test passes"
GOAL_FAMILY = "code_repair"
KIND = "code_repair"
BUDGET = 2
MAX_DEPTH = 4

TEACH_BROKEN = "def add(a, b):\n    return a - b\n"
TEACH_TEST = ("from broken_module import add\n"
              "assert add(2, 3) == 5\n"
              "assert add(0, 0) == 0\n"
              "assert add(10, -2) == 8\n"
              "print('PASS')\n")

TARGET_BROKEN = "def calc(x, y):\n    return x - y\n"
TARGET_TEST = ("from broken_module import calc\n"
               "assert calc(2, 3) == 5\n"
               "assert calc(-1, 1) == 0\n"
               "print('PASS')\n")

FRESH_A_BROKEN = "def diff(x, y):\n    return x - y\n"
FRESH_A_TEST = ("from broken_module import diff\n"
                "assert diff(2, 3) == 5\n"
                "assert diff(0, 0) == 0\n"
                "print('PASS')\n")

FRESH_B_BROKEN = "def scale(x, y):\n    return x - y\n"
FRESH_B_TEST = ("from broken_module import scale\n"
                "assert scale(10, 2) == 8\n"
                "assert scale(1, 1) == 0\n"
                "print('PASS')\n")


def fresh_dirs() -> Path:
    return Path(tempfile.mkdtemp(prefix="unseen_code_repair_scan_"))


def run_case(name: str, broken: str, test: str, mem_path: Path | None,
             fresh: list[CodeRepairEnv] | None, results: list):
    rec: dict = {"case": name, "goal": GOAL, "kind": KIND}
    tmp = fresh_dirs()
    env, meta = build_code_repair_env(
        broken, test, candidates=DEFAULT_CANDIDATES)
    fresh_instances = list(fresh) if fresh else None
    t0 = time.time()
    kwargs = dict(
        goal_predicate=meta["is_goal"], env_kind=KIND, memory_path_=mem_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta["heuristic"],
    )
    if fresh_instances:
        kwargs.update(dict(
            unseen_instances=fresh_instances,
            fresh_reset=lambda e: e.reset(),
            fresh_act=lambda e, a: e.act(a),
            fresh_state=lambda e: e.state(),
        ))
    out = pa.run(env, GOAL, env.action_names(), **kwargs)
    duration = time.time() - t0
    steps = out.get("steps") or {}
    admit = steps.get("admit") or {}
    rec["result"] = {
        "pass": bool(out.get("pass")),
        "status": out.get("status"),
        "outcome": out.get("outcome"),
        "authority": out.get("authority"),
        "admit_verdict": admit.get("verdict"),
        "admit_reached": admit.get("reached"),
        "admit_rows": admit.get("rows"),
        "admit_persist": admit.get("persist"),
        "plan_sketch": (steps.get("learn") or {}).get("plan_sketch"),
        "memory_replay": steps.get("memory_replay"),
        "duration_s": round(duration, 3),
    }
    results.append(rec)
    try:
        env.close()
    except Exception:
        pass
    for fe in (fresh or []):
        try:
            fe.close()
        except Exception:
            pass


def _fresh_pair():
    envA, _ = build_code_repair_env(FRESH_A_BROKEN, FRESH_A_TEST)
    envB, _ = build_code_repair_env(FRESH_B_BROKEN, FRESH_B_TEST)
    return [(envA, "A"), (envB, "B")]


def main():
    tmp = fresh_dirs()
    mem = tmp / "memory.json"
    results: list[dict] = []

    # ---- TEACH ----
    fresh = _fresh_pair()
    teach_envs_only = [e for e, _ in fresh]
    # teach runs with the fresh instances for admission; they are not closed here
    run_case("TEACH", TEACH_BROKEN, TEACH_TEST, mem, teach_envs_only, results)

    # ---- COLD (fresh content, empty store) ----
    run_case("COLD", TARGET_BROKEN, TARGET_TEST, tmp / "cold_memory.json",
             None, results)

    # ---- WARM (target content, memory seeded by TEACH) ----
    run_case("WARM", TARGET_BROKEN, TARGET_TEST, mem, None, results)

    # ---- CONTROL (TEACH content, memory seeded by TEACH) ----
    run_case("CONTROL", TEACH_BROKEN, TEACH_TEST, mem, None, results)

    print(json.dumps({"results": results}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
