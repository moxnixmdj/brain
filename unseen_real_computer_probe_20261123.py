#!/usr/bin/env python3
"""Unseen-content probe on a REAL computer environment (2026-11-23).

The same goal family -- "compress seed.txt into seed.txt.gz" -- over different
instances: same goal, different input CONTENT. Mirrors the shape of
unseen_towers_probe_20261123.py but drives the perfect algorithm through
perfect_algorithm_computer_env_v1 -- a REAL program, a REAL file, a REAL
subprocess, a REAL artifact (gzip on a temp file) -- zero model calls, zero
network, $0.

Per case (seed content A taught, seed content B tested):
  TEACH  cold scan + ACT + VERIFY + admission on 2 fresh content variants
         -> rule admitted on content-unseen instances -> persisted
  COLD   fresh instance, empty store -> cold scan
  WARM   same fresh instance, memory seeded by TEACH
         -> rule replay (instant) or carried model walk or rescan
  CONTROLS (identical content) -> is the instant path real on this env?

Authority NONE. Producer-run sandbox measurement. No capability registered.
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
from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (  # noqa: E402
    drive_perfect_algorithm,
    build_env,
    KIND,
)

GOAL = "compress seed.txt into seed.txt.gz"
GOAL_FAMILY = "compress"
BUDGET = 200

# content A (taught) and content B (tested); control is content A re-run.
TEACH_SEED = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"
TARGET_SEED = b"probe probe probe\ncontent differs\nsame shape\n"
CONTROL_SEED = TEACH_SEED
FRESH_VARIANTS = [
    b"variant one\nrule must not require specific content\n",
    b"variant two\nsame goal family, fresh bytes\n",
]


def fresh_dirs():
    return Path(tempfile.mkdtemp(prefix="unseen_real_computer_"))


def run_case(name: str, teach_seed: bytes, target_seed: bytes, results: list):
    rec = {"case": name, "goal": GOAL, "kind": KIND,
           "teach": {"seed_bytes": len(teach_seed)},
           "target": {"seed_bytes": len(target_seed)}}
    tmp = fresh_dirs()

    # ---- TEACH ----
    teach_mem = tmp / "memory.json"
    env_teach, meta_teach, _ = None, None, None
    env_teach, meta_teach = build_env(GOAL, seed_contents={"seed.txt": teach_seed},
                                     limit=8)
    fresh_instances = []
    for vs in FRESH_VARIANTS:
        fe, _ = build_env(GOAL, seed_contents={"seed.txt": vs}, limit=8)
        fresh_instances.append(fe)
    t0 = time.time()
    out_teach = pa.run(
        env_teach, GOAL, env_teach.action_names(),
        goal_predicate=meta_teach["is_goal"], env_kind=KIND, memory_path_=teach_mem,
        budget=BUDGET, max_depth=4, heuristic=meta_teach["heuristic"],
        unseen_instances=fresh_instances,
        fresh_reset=lambda e: e.reset(),
        fresh_act=lambda e, a: e.act(a),
        fresh_state=lambda e: e.state(),
    )
    teach_dur = time.time() - t0
    admit = (out_teach.get("steps") or {}).get("admit") or {}
    rec["teach"] = {"pass": bool(out_teach.get("pass")),
                    "status": out_teach.get("status"),
                    "outcome": out_teach.get("outcome"),
                    "admit_verdict": admit.get("verdict"),
                    "admit_rows": admit.get("rows"),
                    "admit_reached": admit.get("reached"),
                    "persist": (out_teach.get("steps") or {}).get("admit", {}).get("persist"),
                    "plan_sketch": (out_teach.get("steps") or {}).get("learn", {}).get("plan_sketch"),
                    "duration_s": round(teach_dur, 3)}

    # ---- COLD (target, empty store) ----
    cold_path = tmp / "cold_memory.json"
    env_cold, meta_cold = build_env(GOAL, seed_contents={"seed.txt": target_seed},
                                    limit=8)
    t0 = time.time()
    out_cold = pa.run(
        env_cold, GOAL, env_cold.action_names(),
        goal_predicate=meta_cold["is_goal"], env_kind=KIND, memory_path_=cold_path,
        budget=BUDGET, max_depth=4, heuristic=meta_cold["heuristic"],
    )
    rec["cold"] = {"pass": bool(out_cold.get("pass")),
                   "status": out_cold.get("status"),
                   "outcome": out_cold.get("outcome"),
                   "duration_s": round(time.time() - t0, 3)}

    # ---- WARM (target, memory seeded by TEACH) ----
    warm_path = tmp / "warm_memory.json"
    env_warm, meta_warm = build_env(GOAL, seed_contents={"seed.txt": target_seed},
                                    limit=8)
    t0 = time.time()
    out_warm = pa.run(
        env_warm, GOAL, env_warm.action_names(),
        goal_predicate=meta_warm["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=4,
        heuristic=meta_warm["heuristic"],
    )
    warm_steps = out_warm.get("steps") or {}
    mem_replay = warm_steps.get("memory_replay")
    warmwalk = warm_steps.get("warm_walk")
    rec["warm"] = {"pass": bool(out_warm.get("pass")),
                   "status": out_warm.get("status"),
                   "outcome": out_warm.get("outcome"),
                   "memory_replay": mem_replay,
                   "warm_walk": warmwalk,
                   "duration_s": round(time.time() - t0, 3)}

    # ---- CONTROL (same content as teach, warm) ----
    ctl_path = tmp / "ctl_memory.json"
    env_ctl, meta_ctl = build_env(GOAL, seed_contents={"seed.txt": CONTROL_SEED},
                                 limit=8)
    t0 = time.time()
    out_ctl = pa.run(
        env_ctl, GOAL, env_ctl.action_names(),
        goal_predicate=meta_ctl["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=4,
        heuristic=meta_ctl["heuristic"],
    )
    ctl_steps = out_ctl.get("steps") or {}
    rec["control"] = {"pass": bool(out_ctl.get("pass")),
                      "status": out_ctl.get("status"),
                      "outcome": out_ctl.get("outcome"),
                      "memory_replay": ctl_steps.get("memory_replay"),
                      "duration_s": round(time.time() - t0, 3)}

    for e in (env_teach, env_cold, env_warm, env_ctl, *fresh_instances):
        try:
            e.close()
        except Exception:
            pass
    results.append(rec)


def main():
    results = []
    run_case("alpha_to_beta_unseen_content", TEACH_SEED, TARGET_SEED, results)
    print(json.dumps({"cases": results}, indent=2))
    out = Path("/tmp/unseen_real_computer_probe_result.json")
    out.write_text(json.dumps({"cases": results}, indent=2))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
